"""Unit tests for minitrino.utils module."""

from unittest.mock import MagicMock, patch

import pytest

from minitrino import utils
from minitrino.core.context import MinitrinoContext


class TestCheckLib:
    """Test cases for check_lib function."""

    def test_check_lib_no_ctx(self):
        """Test check_lib raises ValueError when context is None."""
        with pytest.raises(ValueError, match="MinitrinoContext must be provided"):
            utils.check_lib(None)

    @patch("minitrino.utils")
    def test_check_lib_auto_install_called(self, mock_auto_install):
        """Test check_lib calls auto_install_or_update when lib_dir is None."""
        # Create a mock context with lib_dir set to None
        mock_ctx = MagicMock(spec=MinitrinoContext)
        mock_ctx.lib_dir = None
        mock_ctx.library_manager = MagicMock()

        utils.check_lib(mock_ctx)

        mock_ctx.library_manager.auto_install_or_update.assert_called_once()

    @patch("minitrino.utils")
    def test_check_lib_auto_install_not_called(self, mock_auto_install):
        """Test check_lib doesn't call auto_install_or_update when lib_dir is set."""
        # Create a mock context with lib_dir set to a path
        mock_ctx = MagicMock(spec=MinitrinoContext)
        mock_ctx.lib_dir = "/some/path"
        mock_ctx.library_manager = MagicMock()

        utils.check_lib(mock_ctx)

        mock_ctx.library_manager.auto_install_or_update.assert_not_called()
