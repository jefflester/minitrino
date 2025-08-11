"""Tests for auto-install/update library functionality."""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from minitrino import utils as minitrino_utils
from minitrino.cmd.lib_install import cli as lib_install

# LIB_DIR = f"{MINITRINO_USER_DIR}/lib"


# Create a test command group to attach our command to
@click.group()
def cli():
    pass


# Add the lib_install command to our test group
cli.add_command(lib_install, "lib-install")


@pytest.fixture
def temp_lib_dir():
    """Create a temporary directory for testing library operations."""
    temp_dir = tempfile.mkdtemp(prefix="minitrino_test_")
    lib_dir = os.path.join(temp_dir, "lib")
    os.makedirs(lib_dir, exist_ok=True)
    yield lib_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


def create_mock_ctx(temp_lib_dir: str) -> MagicMock:
    """Create a mock MinitrinoContext with necessary attributes."""
    mock_ctx = MagicMock()
    mock_ctx.lib_dir = temp_lib_dir
    mock_ctx.logger = MagicMock()
    mock_ctx.invoke = MagicMock()
    mock_ctx.obj = {"lib_dir": temp_lib_dir}
    return mock_ctx


def test_lib_install_command(temp_lib_dir):
    """Test the lib_install command directly."""
    runner = CliRunner()
    mock_ctx = create_mock_ctx(temp_lib_dir)

    with (
        patch("minitrino.core.context.MinitrinoContext", return_value=mock_ctx),
        patch("minitrino.cmd.lib_install") as mock_download,
    ):

        # Test with version parameter
        result = runner.invoke(cli, ["lib-install", "--version", "1.0.0"])
        assert result.exit_code == 0
        mock_download.assert_called_once_with(
            version="1.0.0", lib_dir=temp_lib_dir, logger=mock_ctx.logger
        )


def test_auto_install_library(temp_lib_dir) -> None:
    """Test auto-installation of library when not installed."""
    # Setup test
    mock_ctx = create_mock_ctx(temp_lib_dir)
    mock_ctx.logger.prompt.return_value = "y"  # Simulate user saying 'yes' to install

    # Mock version checks
    with (
        patch("minitrino.core.utils.cli_ver", return_value="1.0.0"),
        patch("minitrino.core.utils.lib_ver", return_value="NOT INSTALLED"),
        patch("minitrino.core.library.LibraryManager.install") as mock_download,
    ):

        # Call the function
        minitrino_utils._auto_install_or_update_libraries(mock_ctx)

        # Verify library install was called with correct version
        mock_download.assert_called_once_with(
            version="1.0.0", lib_dir=temp_lib_dir, logger=mock_ctx.logger
        )
        mock_ctx.logger.warn.assert_called_with(
            "Minitrino library is not installed. Installing Minitrino libraries... "
        )


def test_auto_update_library(temp_lib_dir) -> None:
    """Test auto-update of library when versions don't match."""
    # Setup test
    mock_ctx = create_mock_ctx(temp_lib_dir)
    mock_ctx.logger.prompt.return_value = "y"  # Simulate user saying 'yes' to update

    # Mock version checks and user input
    with (
        patch("minitrino.utils.cli_ver", return_value="1.0.0"),
        patch("minitrino.utils.lib_ver", return_value="0.9.0"),
        patch("minitrino.utils.validate_yes", return_value=True),
        patch("minitrino.utils.lib_install") as mock_lib_install,
    ):

        # Call the function
        minitrino_utils._auto_install_or_update_libraries(mock_ctx)

        # Verify library install was called with correct version
        mock_lib_install.assert_called_once_with(version="1.0.0")
        mock_ctx.logger.info.assert_called_with(
            "Overwriting existing Minitrino library to version 1.0.0"
        )


def test_skip_update_library(temp_lib_dir) -> None:
    """Test skipping library update when versions don't match but user declines."""
    # Setup test
    mock_ctx = create_mock_ctx(temp_lib_dir)
    mock_ctx.logger.prompt.return_value = "n"  # Simulate user saying 'no' to update

    # Mock version checks and user input
    with (
        patch("minitrino.utils.cli_ver", return_value="1.0.0"),
        patch("minitrino.utils.lib_ver", return_value="0.9.0"),
        patch("minitrino.utils.validate_yes", return_value=False),
        patch("minitrino.utils.lib_install") as mock_lib_install,
    ):

        # Call the function
        minitrino_utils._auto_install_or_update_libraries(mock_ctx)

        # Verify library install was not called
        mock_lib_install.assert_not_called()
        mock_ctx.logger.warn.assert_called_with(
            "It is highly recommended to use matching CLI and library versions. "
            "Mismatched versions are likely to cause errors. "
            "To install the library manually, run `minitrino lib-install`."
        )


def test_matching_versions_no_action(temp_lib_dir) -> None:
    """Test that no action is taken when versions match."""
    # Setup test
    mock_ctx = create_mock_ctx(temp_lib_dir)

    # Mock version checks
    with (
        patch("minitrino.utils.cli_ver", return_value="1.0.0"),
        patch("minitrino.utils.lib_ver", return_value="1.0.0"),
        patch("minitrino.utils.lib_install") as mock_lib_install,
    ):

        # Call the function
        minitrino_utils._auto_install_or_update_libraries(mock_ctx)

        # Verify no install was attempted
        mock_lib_install.assert_not_called()
        mock_ctx.logger.debug.assert_called_with(
            "CLI and library versions match. No action required."
        )
