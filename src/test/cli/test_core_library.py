"""Unit tests for minitrino.core.library module."""

from unittest.mock import MagicMock, patch

import pytest

from minitrino.core.context import MinitrinoContext
from minitrino.core.library import LibraryManager


class TestLibraryManagerAutoInstallOrUpdate:
    """Test cases for LibraryManager.auto_install_or_update method."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock MinitrinoContext with common attributes."""
        ctx = MagicMock(spec=MinitrinoContext)
        ctx.logger = MagicMock()
        ctx.lib_dir = "/path/to/lib"
        return ctx

    @patch("minitrino.core.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.core.library.utils.lib_ver", return_value="NOT INSTALLED")
    def test_auto_install_not_installed(self, mock_lib_ver, mock_cli_ver, mock_ctx):
        """Test auto_install_or_update when library is not installed."""
        manager = LibraryManager(mock_ctx)
        manager.install = MagicMock()

        manager.auto_install_or_update()

        mock_ctx.logger.warn.assert_called_once()
        manager.install.assert_called_once_with(version="1.0.0")

    @patch("minitrino.core.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.core.library.utils.lib_ver", return_value="0.9.0")
    @patch("minitrino.core.library.utils.validate_yes", return_value=True)
    def test_auto_install_version_mismatch_upgrade(
        self, mock_validate, mock_lib_ver, mock_cli_ver, mock_ctx
    ):
        """Test auto_install_or_update when versions don't match
        and user chooses to upgrade."""
        manager = LibraryManager(mock_ctx)
        manager.install = MagicMock()

        manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        manager.install.assert_called_once_with(version="1.0.0")
        mock_ctx.logger.info.assert_called_once_with(
            "Overwriting existing Minitrino library to version 1.0.0"
        )

    @patch("minitrino.core.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.core.library.utils.lib_ver", return_value="0.9.0")
    @patch("minitrino.core.library.utils.validate_yes", return_value=False)
    def test_auto_install_version_mismatch_no_upgrade(
        self, mock_validate, mock_lib_ver, mock_cli_ver, mock_ctx
    ):
        """Test auto_install_or_update when versions don't match
        and user chooses not to upgrade."""
        manager = LibraryManager(mock_ctx)
        manager.install = MagicMock()

        manager.auto_install_or_update()

        mock_ctx.logger.prompt_msg.assert_called_once()
        manager.install.assert_not_called()
        mock_ctx.logger.warn.assert_called_once()
        assert (
            "highly recommended to use matching CLI and library versions"
            in mock_ctx.logger.warn.call_args[0][0]
        )

    @patch("minitrino.core.library.utils.cli_ver", return_value="1.0.0")
    @patch("minitrino.core.library.utils.lib_ver", return_value="1.0.0")
    def test_auto_install_versions_match(self, mock_lib_ver, mock_cli_ver, mock_ctx):
        """Test auto_install_or_update when versions match."""
        manager = LibraryManager(mock_ctx)
        manager.install = MagicMock()

        manager.auto_install_or_update()

        manager.install.assert_not_called()
        mock_ctx.logger.debug.assert_called_once_with(
            "CLI and library versions match. No action required."
        )
