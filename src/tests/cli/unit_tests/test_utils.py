"""Unit tests for minitrino.utils module."""

from unittest.mock import MagicMock, patch

import pytest
from minitrino import utils
from minitrino.core.context import MinitrinoContext


@pytest.fixture
def mock_ctx_with_lib():
    """Create a mock context with library directory set."""
    ctx = MagicMock(spec=MinitrinoContext)
    ctx.lib_dir = "/some/path"
    ctx.library_manager = MagicMock()
    return ctx


@pytest.fixture
def mock_ctx_without_lib():
    """Create a mock context without library directory."""
    ctx = MagicMock(spec=MinitrinoContext)
    ctx.lib_dir = None
    ctx.library_manager = MagicMock()
    return ctx


class TestCheckLib:
    """Test cases for check_lib function."""

    def test_check_lib_no_ctx(self):
        """Test check_lib raises ValueError when context is None."""
        with pytest.raises(ValueError, match="MinitrinoContext must be provided"):
            utils.check_lib(None)

    @patch("minitrino.utils")
    def test_check_lib_auto_install_called(
        self, mock_auto_install, mock_ctx_without_lib
    ):
        """Test check_lib calls auto_install_or_update when lib_dir is None."""
        utils.check_lib(mock_ctx_without_lib)

        mock_ctx_without_lib.library_manager.auto_install_or_update.assert_called_once()

    @patch("minitrino.utils")
    def test_check_lib_auto_install_not_called(
        self, mock_auto_install, mock_ctx_with_lib
    ):
        """Test check_lib doesn't call auto_install_or_update when lib_dir is set."""
        utils.check_lib(mock_ctx_with_lib)

        mock_ctx_with_lib.library_manager.auto_install_or_update.assert_not_called()
