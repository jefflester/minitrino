"""Tests for the LibraryManager class in minitrino.library.

This test suite verifies the functionality of the LibraryManager class, including
library installation, version management, and error handling.
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from minitrino.errors import MinitrinoError, UserError
from minitrino.library import LibraryManager


@pytest.fixture
def mock_ctx(tmp_path, mock_logger):
    """Create a mock MinitrinoContext with common attributes."""
    from minitrino.context import MinitrinoContext

    ctx = MagicMock(spec=MinitrinoContext)
    ctx.logger = mock_logger
    ctx.lib_dir = str(tmp_path / "lib")
    ctx.minitrino_user_dir = str(tmp_path / "minitrino")
    ctx.effective_assume_yes = False
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

    @patch("minitrino.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.library.utils.lib_ver")
    @patch("minitrino.library.utils.validate_yes", return_value=True)
    def test_not_installed_accept(
        self, mock_validate, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Not installed, user accepts prompt → install."""
        mock_lib_ver.return_value = "NOT INSTALLED"
        library_manager.install = MagicMock()

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        library_manager.install.assert_called_once_with(version="1.0.0")

    @patch("minitrino.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.library.utils.lib_ver")
    @patch("minitrino.library.utils.validate_yes", return_value=False)
    def test_not_installed_decline_raises(
        self, mock_validate, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Not installed, user declines → UserError, decline cache written."""
        mock_lib_ver.return_value = "NOT INSTALLED"
        library_manager.install = MagicMock()
        library_manager._write_decline_cache = MagicMock()

        with pytest.raises(UserError, match="required for this operation"):
            library_manager.auto_install_or_update()

        library_manager.install.assert_not_called()
        library_manager._write_decline_cache.assert_called_once_with(
            "1.0.0", "NOT INSTALLED"
        )

    @patch("minitrino.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.library.utils.validate_yes", return_value=True)
    def test_not_installed_when_lib_dir_raises(
        self, mock_validate, mock_cli_ver, library_manager, mock_ctx
    ):
        """lib_dir raising UserError (no library present) is treated as
        NOT INSTALLED so the install prompt stays reachable.

        Regression for the bug where accessing ``ctx.lib_dir`` raised before
        the NOT INSTALLED branch could run, so a fresh machine got a bare
        error instead of an install prompt.
        """
        from unittest.mock import PropertyMock

        library_manager.install = MagicMock()
        library_manager._read_decline_cache = MagicMock(return_value=None)

        lib_dir_prop = PropertyMock(
            side_effect=UserError("requires a library to be installed")
        )
        with patch.object(type(mock_ctx), "lib_dir", lib_dir_prop, create=True):
            library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        library_manager.install.assert_called_once_with(version="1.0.0")

    @patch("minitrino.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.library.utils.lib_ver", return_value="1.0.0")
    def test_versions_match(
        self, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Versions match → no-op, debug log."""
        library_manager.install = MagicMock()

        library_manager.auto_install_or_update()

        library_manager.install.assert_not_called()
        mock_ctx.logger.debug.assert_called_once_with(
            "CLI and library versions match. No action required."
        )

    @patch("minitrino.library.utils.cli_ver", return_value="1.1.0")
    @patch("minitrino.library.utils.lib_ver")
    @patch("minitrino.library.utils.validate_yes", return_value=True)
    def test_version_mismatch_upgrade(
        self, mock_validate, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Mismatch, no fresh cache, user accepts → install."""
        mock_lib_ver.return_value = "1.0.0"
        library_manager.install = MagicMock()
        library_manager._read_decline_cache = MagicMock(return_value=None)

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        library_manager.install.assert_called_once_with(
            version="1.1.0", _skip_confirm=True
        )

    @patch("minitrino.library.utils.cli_ver", return_value="1.1.0")
    @patch("minitrino.library.utils.lib_ver")
    @patch("minitrino.library.utils.validate_yes", return_value=False)
    def test_version_mismatch_decline(
        self, mock_validate, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Mismatch, no fresh cache, user declines → cache written, warn."""
        mock_lib_ver.return_value = "1.0.0"
        library_manager.install = MagicMock()
        library_manager._read_decline_cache = MagicMock(return_value=None)
        library_manager._write_decline_cache = MagicMock()

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        library_manager.install.assert_not_called()
        library_manager._write_decline_cache.assert_called_once_with("1.1.0", "1.0.0")
        mock_ctx.logger.warn.assert_called_once()
        assert (
            "Mismatched CLI and library versions"
            in mock_ctx.logger.warn.call_args[0][0]
        )

    @patch("minitrino.library.utils.cli_ver", return_value="1.1.0")
    @patch("minitrino.library.utils.lib_ver")
    def test_mismatch_fresh_cache_skips_prompt(
        self, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Fresh decline cache → no prompt, debug log only."""
        mock_lib_ver.return_value = "1.0.0"
        library_manager.install = MagicMock()
        library_manager._read_decline_cache = MagicMock(
            return_value={"declined_at": datetime.now(timezone.utc).isoformat()}
        )
        library_manager._decline_is_fresh = MagicMock(return_value=True)

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_not_called()
        library_manager.install.assert_not_called()
        mock_ctx.logger.debug.assert_called_once()

    @patch("minitrino.library.utils.cli_ver", return_value="1.1.0")
    @patch("minitrino.library.utils.lib_ver")
    @patch("minitrino.library.utils.validate_yes", return_value=True)
    def test_mismatch_stale_cache_reprompts(
        self, mock_validate, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """Stale decline cache → prompt fires again."""
        mock_lib_ver.return_value = "1.0.0"
        library_manager.install = MagicMock()
        library_manager._read_decline_cache = MagicMock(
            return_value={"declined_at": "2020-01-01T00:00:00+00:00"}
        )
        library_manager._decline_is_fresh = MagicMock(return_value=False)

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        library_manager.install.assert_called_once_with(
            version="1.1.0", _skip_confirm=True
        )

    @patch("minitrino.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.library.utils.lib_ver")
    def test_assume_yes_not_installed(
        self, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """assume_yes + not installed → auto-install, no prompt."""
        mock_lib_ver.return_value = "NOT INSTALLED"
        mock_ctx.effective_assume_yes = True
        library_manager.install = MagicMock()

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_not_called()
        library_manager.install.assert_called_once_with(version="1.0.0")

    @patch("minitrino.library.utils.cli_ver", return_value="1.1.0")
    @patch("minitrino.library.utils.lib_ver")
    def test_assume_yes_mismatch(
        self, mock_lib_ver, mock_cli_ver, library_manager, mock_ctx
    ):
        """assume_yes + mismatch → auto-install, no prompt."""
        mock_lib_ver.return_value = "1.0.0"
        mock_ctx.effective_assume_yes = True
        library_manager.install = MagicMock()

        library_manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_not_called()
        library_manager.install.assert_called_once_with(
            version="1.1.0", _skip_confirm=True
        )


class TestDeclineCache:
    """Tests for the decline cache helper methods."""

    def test_write_and_read_cache(self, library_manager, mock_ctx, tmp_path):
        mock_ctx.minitrino_user_dir = str(tmp_path)
        library_manager._write_decline_cache("1.1.0", "1.0.0")
        cache = library_manager._read_decline_cache()
        assert cache is not None
        assert cache["cli_ver"] == "1.1.0"
        assert cache["lib_ver"] == "1.0.0"
        assert "declined_at" in cache

    def test_read_missing_cache(self, library_manager, mock_ctx, tmp_path):
        mock_ctx.minitrino_user_dir = str(tmp_path)
        assert library_manager._read_decline_cache() is None

    def test_decline_is_fresh_within_ttl(self, library_manager):
        cache = {"declined_at": datetime.now(timezone.utc).isoformat()}
        assert library_manager._decline_is_fresh(cache) is True

    def test_decline_is_stale_past_ttl(self, library_manager):
        old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        cache = {"declined_at": old}
        assert library_manager._decline_is_fresh(cache) is False

    def test_decline_is_fresh_bad_data(self, library_manager):
        assert library_manager._decline_is_fresh({}) is False
        assert library_manager._decline_is_fresh({"declined_at": "garbage"}) is False

    def test_clear_cache(self, library_manager, mock_ctx, tmp_path):
        mock_ctx.minitrino_user_dir = str(tmp_path)
        library_manager._write_decline_cache("1.1.0", "1.0.0")
        assert library_manager._read_decline_cache() is not None
        library_manager._clear_decline_cache()
        assert library_manager._read_decline_cache() is None

    def test_clear_cache_missing_file(self, library_manager, mock_ctx, tmp_path):
        mock_ctx.minitrino_user_dir = str(tmp_path)
        library_manager._clear_decline_cache()


class TestLibraryReleases:
    """Tests for library release management."""

    @patch("minitrino.library.requests.get")
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

    @patch("minitrino.library.requests.get")
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

    @patch("minitrino.library.LibraryManager._download_file")
    @patch("minitrino.library.LibraryManager._extract_tarball")
    @patch("minitrino.library.shutil.move")
    @patch("minitrino.library.LibraryManager._cleanup")
    @patch("os.path.isdir", return_value=True)
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
        mock_cleanup.assert_called_once_with(
            expected_tarball, f"minitrino-{version}", trigger_error=False
        )

    @patch("builtins.open")
    @patch("minitrino.library.requests.get")
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

    @patch("os.path.isfile", return_value=True)
    @patch("os.remove", side_effect=OSError("Failed to remove"))
    def test_cleanup_errors_swallowed_when_not_triggering(
        self, mock_remove, mock_isfile, library_manager
    ):
        """trigger_error=False must swallow cleanup errors.

        Regression: the success-path cleanup in download_and_extract runs with
        trigger_error=False so a cosmetic cleanup failure can never propagate
        and cause install() to roll back an already-successful install.
        """
        library_manager._cleanup("/path/to/file.tar.gz", trigger_error=False)


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
        manager.validate = MagicMock()  # type: ignore[method-assign]
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

    def test_prune_ranks_by_name_not_mtime(self, install_manager, tmp_path):
        """Pruning must rank backups by the timestamp embedded in the name,
        not by filesystem mtime.

        Regression: tarball extraction preserves the release's mtime, so a
        freshly created backup can carry an older mtime than an older-named
        one. Here the newer-named backup is given an OLD mtime and the
        older-named backup a NEW mtime; name-based ranking must still keep
        the newer-named backup.
        """
        newer_name = tmp_path / "lib.bak.20250101-000000"
        older_name = tmp_path / "lib.bak.20200101-000000"
        newer_name.mkdir()
        older_name.mkdir()
        os.utime(newer_name, (1_000, 1_000))  # old mtime
        os.utime(older_name, (9_000_000, 9_000_000))  # new mtime

        install_manager._prune_backups(keep=1)

        remaining = sorted(
            p.name for p in tmp_path.iterdir() if p.name.startswith("lib.bak.")
        )
        assert remaining == [
            "lib.bak.20250101-000000"
        ], "prune should keep the newest by name, not by mtime"

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

    def test_install_clears_decline_cache(self, install_manager, tmp_path):
        """Successful install removes any stale decline cache."""
        cache_path = tmp_path / "lib_sync_state.json"
        cache_path.write_text('{"declined_at": "2020-01-01T00:00:00+00:00"}')

        self._stub_download(install_manager, marker="new")
        install_manager.install("1.0.0")

        assert not cache_path.exists()
