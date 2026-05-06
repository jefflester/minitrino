"""Tests for the LibraryManager class in minitrino.core.library.

This test suite verifies the functionality of the LibraryManager class, including
library installation, version management, and error handling.
"""

import os
from unittest.mock import MagicMock, call, patch

import pytest
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.library import LibraryManager


@pytest.fixture
def mock_ctx(tmp_path, mock_logger):
    """Create a mock MinitrinoContext with common attributes."""
    from minitrino.core.context import MinitrinoContext

    ctx = MagicMock(spec=MinitrinoContext)
    ctx.logger = mock_logger
    ctx.lib_dir = str(tmp_path / "lib")
    ctx.minitrino_user_dir = str(tmp_path / "minitrino")
    ctx.config = MagicMock()
    ctx.config.get_library_version.return_value = None
    return ctx


@pytest.fixture
def library_manager(mock_ctx):
    """Create a LibraryManager instance with a mock context."""
    manager = LibraryManager(mock_ctx)
    manager._ctx = mock_ctx  # Ensure _ctx is properly set
    return manager


class TestAutoInstallOrUpdate:
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
        """Test auto_install when versions don't match and user chooses to upgrade."""
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
        """Test auto_install when versions don't match and user chooses not to
        upgrade."""
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


class TestLibraryReleases:
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


class TestLibraryValidation:
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
        with (
            patch.object(library_manager, "list_releases", return_value=["1.0.0"]),
            pytest.raises(MinitrinoError, match="not found on GitHub"),
        ):
            library_manager.validate("9.9.9")


class TestFileOperations:
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

        expected_tarball = f"{mock_ctx.minitrino_user_dir}/{version}.tar.gz"
        expected_lib_dir = f"{mock_ctx.minitrino_user_dir}/minitrino-{version}/src/lib"

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


class TestInstallBackups:
    """Tests for install()'s backup-and-rename, restore-on-failure, and backup pruning
    behavior.

    These tests use a real tmp_path filesystem instead of mocking os.rename / os.listdir
    so the directory shuffling is exercised end-to-end.
    """

    @pytest.fixture
    def install_ctx(self, mock_ctx, tmp_path):
        """Configure mock_ctx with a real tmp dir for filesystem ops."""
        mock_ctx.minitrino_user_dir = str(tmp_path)
        mock_ctx.effective_assume_yes = True
        return mock_ctx

    @pytest.fixture
    def install_manager(self, install_ctx):
        """LibraryManager wired to the tmp-dir context, validate stubbed."""
        manager = LibraryManager(install_ctx)
        manager._ctx = install_ctx
        manager.validate = MagicMock()
        return manager

    def _stub_download(self, manager, marker: str = "v"):
        """Make download_and_extract create a real lib dir with a marker.

        Lets tests assert against actual on-disk state to verify which version of the
        lib is in place after success or rollback.
        """

        def _fake(version):
            lib_dir = os.path.join(manager._ctx.minitrino_user_dir, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            with open(os.path.join(lib_dir, "version"), "w") as f:
                f.write(f"{marker}-{version}")

        manager.download_and_extract = MagicMock(side_effect=_fake)

    def test_fresh_install_no_backup(self, install_manager, tmp_path):
        """No existing lib → no backup directory is created."""
        self._stub_download(install_manager, marker="new")
        install_manager.install("1.0.0")

        assert (tmp_path / "lib" / "version").read_text() == "new-1.0.0"
        backups = [p.name for p in tmp_path.iterdir() if p.name.startswith("lib.bak.")]
        assert backups == []

    def test_existing_lib_backed_up(self, install_manager, tmp_path):
        """Existing lib renamed to lib.bak.<ts>; new lib in place."""
        old = tmp_path / "lib"
        old.mkdir()
        (old / "version").write_text("old-0.9.0")

        self._stub_download(install_manager, marker="new")
        install_manager.install("1.0.0")

        assert (tmp_path / "lib" / "version").read_text() == "new-1.0.0"
        backups = sorted(p for p in tmp_path.iterdir() if p.name.startswith("lib.bak."))
        assert len(backups) == 1
        assert (backups[0] / "version").read_text() == "old-0.9.0"

    def test_install_failure_restores_backup(self, install_manager, tmp_path):
        """download_and_extract failure → backup restored to lib_dir."""
        old = tmp_path / "lib"
        old.mkdir()
        (old / "version").write_text("old-0.9.0")

        install_manager.download_and_extract = MagicMock(
            side_effect=MinitrinoError("network kaboom")
        )

        with pytest.raises(MinitrinoError, match="network kaboom"):
            install_manager.install("1.0.0")

        assert (tmp_path / "lib" / "version").read_text() == "old-0.9.0"
        backups = [p for p in tmp_path.iterdir() if p.name.startswith("lib.bak.")]
        assert backups == [], "restore should leave no lib.bak.* behind"

    def test_prune_keeps_two_newest(self, install_manager, tmp_path):
        """After install, only the BACKUP_RETENTION newest backups remain."""
        # Pre-create 3 stale backups with monotonically increasing mtimes.
        for i in range(3):
            d = tmp_path / f"lib.bak.2020010{i}-000000"
            d.mkdir()
            (d / "marker").write_text(str(i))
            os.utime(d, (1000 + i * 1000, 1000 + i * 1000))
        # Existing lib that this install will back up (becoming the 4th).
        old = tmp_path / "lib"
        old.mkdir()

        self._stub_download(install_manager, marker="new")
        install_manager.install("1.0.0")

        backups = sorted(p for p in tmp_path.iterdir() if p.name.startswith("lib.bak."))
        assert len(backups) == 2, f"expected 2 backups, got {[b.name for b in backups]}"
        # The newest pruned backup was the just-renamed old lib + the
        # most-recent pre-existing one. The two oldest pre-existing ones
        # (markers 0 and 1) should be gone.
        markers = sorted(
            (b / "marker").read_text() for b in backups if (b / "marker").exists()
        )
        assert "0" not in markers and "1" not in markers

    def test_prompt_decline_skips_install(self, install_manager, tmp_path, mock_ctx):
        """User answers N → no install, no backup, lib untouched."""
        mock_ctx.effective_assume_yes = False
        mock_ctx.logger.prompt_msg.return_value = "n"

        old = tmp_path / "lib"
        old.mkdir()
        (old / "version").write_text("old-0.9.0")

        install_manager.download_and_extract = MagicMock()
        install_manager.install("1.0.0")

        install_manager.download_and_extract.assert_not_called()
        assert (tmp_path / "lib" / "version").read_text() == "old-0.9.0"
        backups = [p for p in tmp_path.iterdir() if p.name.startswith("lib.bak.")]
        assert backups == []

    def test_assume_yes_skips_prompt(self, install_manager, tmp_path, mock_ctx):
        """effective_assume_yes=True → prompt_msg never called."""
        old = tmp_path / "lib"
        old.mkdir()

        self._stub_download(install_manager, marker="new")
        install_manager.install("1.0.0")

        mock_ctx.logger.prompt_msg.assert_not_called()
