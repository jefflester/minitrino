"""
Tests for the LibraryManager class in minitrino.core.library.

This test suite verifies the functionality of the LibraryManager class,
including library installation, version management, and error handling.
"""

import os
from unittest.mock import MagicMock, call, patch

import pytest

from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.library import LibraryManager


class TestLibraryManagerBase:
    """Base test class with common fixtures and utilities."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock MinitrinoContext with common attributes."""
        ctx = MagicMock(spec=MinitrinoContext)
        ctx.logger = MagicMock()
        ctx.lib_dir = "/path/to/lib"
        ctx.minitrino_user_dir = "/path/to/minitrino"
        ctx.config = MagicMock()
        ctx.config.get_library_version.return_value = None
        return ctx

    @pytest.fixture
    def library_manager(self, mock_ctx):
        """Create a LibraryManager instance with a mock context."""
        manager = LibraryManager(mock_ctx)
        manager._ctx = mock_ctx  # Ensure _ctx is properly set
        return manager


class TestAutoInstallOrUpdate(TestLibraryManagerBase):
    """Tests for the auto_install_or_update method."""

    @patch("minitrino.core.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.core.library.utils.lib_ver")
    def test_not_installed(self, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx):
        """Test auto_install when library is not installed."""
        mock_lib_ver.return_value = "NOT INSTALLED"
        library_manager.install = MagicMock()

        library_manager.auto_install_or_update()

        mock_ctx.logger.warn.assert_called_once()
        library_manager.install.assert_called_once_with(version="1.0.0")

    @patch("minitrino.core.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.core.library.utils.lib_ver", return_value="1.0.0")
    def test_versions_match(
        self, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Test auto_install when versions match."""
        library_manager.install = MagicMock()

        library_manager.auto_install_or_update()

        library_manager.install.assert_not_called()
        mock_ctx.logger.debug.assert_called_once_with(
            "CLI and library versions match. No action required."
        )

    @patch("minitrino.core.library.utils.cli_ver", return_value="1.1.0")
    @patch("minitrino.core.library.utils.lib_ver")
    @patch("minitrino.core.library.utils.validate_yes", return_value=True)
    def test_version_mismatch_upgrade(
        self, mock_validate, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Test auto_install when versions don't match and user
        chooses to upgrade."""
        mock_lib_ver.return_value = "1.0.0"
        library_manager.install = MagicMock()

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        library_manager.install.assert_called_once_with(version="1.1.0")
        mock_ctx.logger.info.assert_called_once_with(
            "Overwriting existing Minitrino library to version 1.1.0"
        )

    @patch("minitrino.core.library.utils.cli_ver", return_value="1.1.0")
    @patch("minitrino.core.library.utils.lib_ver")
    @patch("minitrino.core.library.utils.validate_yes", return_value=False)
    def test_version_mismatch_no_upgrade(
        self, mock_validate, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Test auto_install when versions don't match
        and user chooses not to upgrade."""
        mock_lib_ver.return_value = "1.0.0"
        library_manager.install = MagicMock()

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        library_manager.install.assert_not_called()
        mock_ctx.logger.warn.assert_called_once()
        assert (
            "highly recommended to use matching CLI and library versions"
            in mock_ctx.logger.warn.call_args[0][0]
        )


class TestLibraryReleases(TestLibraryManagerBase):
    """Tests for library release management."""

    @patch("minitrino.core.library.requests.get")
    def test_list_releases_success(self, mock_get, library_manager):
        """Test successful listing of releases from GitHub."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"tag_name": "1.0.0"},
            {"tag_name": "0.9.0"},
            {"tag_name": "1.1.0"},
        ]
        mock_get.return_value = mock_response

        releases = library_manager.list_releases()

        assert releases == ["0.9.0", "1.0.0", "1.1.0"]
        mock_get.assert_called_once()

    @patch("minitrino.core.library.requests.get")
    def test_list_releases_pagination(self, mock_get, library_manager):
        """Test that list_releases handles pagination correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"tag_name": "1.0.0"}, {"tag_name": "0.9.0"}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        releases = library_manager.list_releases()

        assert sorted(releases) == ["0.9.0", "1.0.0"]
        mock_get.assert_called_once()


class TestLibraryValidation(TestLibraryManagerBase):
    """Tests for library version validation."""

    def test_validate_valid_version(self, library_manager):
        """Test validation of a valid version."""
        with patch.object(library_manager, "list_releases", return_value=["1.0.0"]):
            library_manager.validate("1.0.0")  # Should not raise

    def test_validate_invalid_format(self, library_manager):
        """Test validation of an invalid version format."""
        with pytest.raises(UserError, match="must be in X.Y.Z format"):
            library_manager.validate("invalid-version")

    def test_validate_nonexistent_version(self, library_manager):
        """Test validation of a version that doesn't exist."""
        with patch.object(library_manager, "list_releases", return_value=["1.0.0"]):
            with pytest.raises(MinitrinoError, match="not found on GitHub"):
                library_manager.validate("9.9.9")


class TestFileOperations(TestLibraryManagerBase):
    """Tests for file operations like download, extract, and cleanup."""

    @patch("minitrino.core.library.LibraryManager._download_file")
    @patch("minitrino.core.library.LibraryManager._extract_tarball")
    @patch("minitrino.core.library.shutil.move")
    @patch("minitrino.core.library.LibraryManager._cleanup")
    @patch("os.path.isdir", return_value=False)
    def test_download_and_extract_success(
        self,
        mock_isdir,
        mock_cleanup,
        mock_move,
        mock_extract,
        mock_download,
        library_manager,
        mock_ctx,
    ):
        """Test successful download and extraction of a library version."""
        version = "1.0.0"
        library_manager.download_and_extract(version)

        expected_tarball = f"/path/to/minitrino/{version}.tar.gz"
        expected_lib_dir = f"/path/to/minitrino/minitrino-{version}/src/lib"

        mock_download.assert_called_once()
        mock_extract.assert_called_once_with(
            expected_tarball, mock_ctx.minitrino_user_dir
        )
        mock_move.assert_called_once_with(
            expected_lib_dir, os.path.join(mock_ctx.minitrino_user_dir, "lib")
        )
        mock_cleanup.assert_called_once_with(expected_tarball, f"minitrino-{version}")

    @patch("builtins.open")
    @patch("minitrino.core.library.requests.get")
    def test_download_file_success(self, mock_get, mock_open, library_manager):
        """Test successful file download."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        url = "https://example.com/file.tar.gz"
        dest = "/path/to/destination/file.tar.gz"
        library_manager._download_file(url, dest)

        mock_get.assert_called_once_with(url, stream=True)
        assert mock_file.write.call_count == 2
        mock_file.write.assert_has_calls([call(b"chunk1"), call(b"chunk2")])

    @patch("tarfile.open")
    def test_extract_tarball(self, mock_tarfile, library_manager):
        """Test tarball extraction."""
        tarball_path = "/path/to/file.tar.gz"
        extract_dir = "/path/to/extract"

        mock_tar = MagicMock()
        mock_tarfile.return_value.__enter__.return_value = mock_tar

        LibraryManager._extract_tarball(tarball_path, extract_dir)

        mock_tarfile.assert_called_once_with(tarball_path, "r:gz")
        mock_tar.extractall.assert_called_once_with(
            path=extract_dir, filter="fully_trusted"
        )

    @patch("os.path.isfile", return_value=True)
    @patch("os.path.exists", return_value=True)
    @patch("os.remove")
    @patch("shutil.rmtree")
    def test_cleanup_success(
        self,
        mock_rmtree,
        mock_remove,
        mock_exists,
        mock_isfile,
        library_manager,
        mock_ctx,
    ):
        """Test successful cleanup of files and directories."""
        tarball = "/path/to/file.tar.gz"
        file_basename = "minitrino-1.0.0"

        library_manager._cleanup(tarball, file_basename)

        expected_calls = [
            call(tarball),
            call(os.path.join(mock_ctx.minitrino_user_dir, file_basename)),
        ]
        mock_remove.assert_has_calls(expected_calls, any_order=True)

    @patch("os.path.isfile", return_value=True)
    @patch("os.remove", side_effect=OSError("Failed to remove"))
    def test_cleanup_with_errors(self, mock_remove, mock_isfile, library_manager):
        """Test cleanup with file removal errors."""
        tarball = "/path/to/file.tar.gz"

        with pytest.raises(MinitrinoError, match="Failed to remove tarball"):
            library_manager._cleanup(tarball)
