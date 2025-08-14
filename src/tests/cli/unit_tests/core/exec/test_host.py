"""Unit tests for host command execution.

Tests the HostCommandExecutor class for executing commands on the host system.
"""

import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from minitrino.core.errors import MinitrinoError
from minitrino.core.exec.host import HostCommandExecutor


class TestHostCommandExecutor:
    """Test suite for HostCommandExecutor."""

    def test_executor_initialization(self):
        """Test creating a HostCommandExecutor."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        executor = HostCommandExecutor(mock_ctx)

        assert executor._ctx == mock_ctx

    @patch("subprocess.run")
    def test_execute_simple_command(self, mock_run):
        """Test executing a simple command."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Hello, World!", stderr=""
        )

        executor = HostCommandExecutor(mock_ctx)
        results = executor.execute(["echo", "Hello, World!"])

        assert len(results) == 1
        assert results[0].exit_code == 0
        assert results[0].output == "Hello, World!"
        assert results[0].error == ""
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_execute_command_with_error(self, mock_run):
        """Test executing a command that returns an error."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Command not found"
        )

        executor = HostCommandExecutor(mock_ctx)
        results = executor.execute(["nonexistent_command"])

        assert len(results) == 1
        assert results[0].exit_code == 1
        assert results[0].output == ""
        assert results[0].error == "Command not found"

    @patch("subprocess.run")
    def test_execute_multiple_commands(self, mock_run):
        """Test executing multiple commands."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="output1", stderr=""),
            MagicMock(returncode=0, stdout="output2", stderr=""),
        ]

        executor = HostCommandExecutor(mock_ctx)
        results = executor.execute(["echo", "one"], ["echo", "two"])

        assert len(results) == 2
        assert results[0].output == "output1"
        assert results[1].output == "output2"
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_execute_with_environment(self, mock_run):
        """Test executing with custom environment variables."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(returncode=0, stdout="VALUE", stderr="")

        executor = HostCommandExecutor(mock_ctx)
        _ = executor.execute(["printenv", "MY_VAR"], environment={"MY_VAR": "VALUE"})

        # Check that environment was passed to subprocess
        call_kwargs = mock_run.call_args[1]
        assert "env" in call_kwargs
        assert call_kwargs["env"]["MY_VAR"] == "VALUE"

    @patch("subprocess.run")
    def test_execute_with_suppress_output(self, mock_run):
        """Test executing with output suppression."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        executor = HostCommandExecutor(mock_ctx)
        results = executor.execute(["echo", "test"], suppress_output=True)

        # Output should still be captured, just not printed
        assert results[0].output == "output"
        # Check that logger methods weren't called for output
        mock_ctx.logger.msg.assert_not_called()

    @patch("subprocess.run")
    def test_execute_with_trigger_error(self, mock_run):
        """Test executing with error triggering enabled."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error occurred"
        )

        executor = HostCommandExecutor(mock_ctx)

        with pytest.raises(MinitrinoError):
            executor.execute(["false"], trigger_error=True)

    @patch("subprocess.run")
    def test_execute_with_trigger_error_success(self, mock_run):
        """Test that trigger_error doesn't raise on success."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

        executor = HostCommandExecutor(mock_ctx)
        results = executor.execute(["true"], trigger_error=True)

        assert results[0].exit_code == 0

    @patch("subprocess.Popen")
    def test_execute_interactive(self, mock_popen):
        """Test executing in interactive mode."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        executor = HostCommandExecutor(mock_ctx)
        results = executor.execute(["bash"], interactive=True)

        # Interactive mode uses Popen instead of run
        mock_popen.assert_called_once()
        assert len(results) == 1
        assert results[0].exit_code == 0

    @patch("subprocess.run")
    def test_execute_with_timeout(self, mock_run):
        """Test executing with timeout."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["sleep", "10"], timeout=1)

        executor = HostCommandExecutor(mock_ctx)

        with pytest.raises(subprocess.TimeoutExpired):
            executor.execute(["sleep", "10"], timeout=1)

    @patch("subprocess.run")
    def test_execute_with_cwd(self, mock_run):
        """Test executing with working directory."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(returncode=0, stdout="/tmp", stderr="")

        executor = HostCommandExecutor(mock_ctx)
        _ = executor.execute(["pwd"], cwd="/tmp")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("cwd") == "/tmp"

    @patch("subprocess.run")
    def test_execute_with_shell(self, mock_run):
        """Test executing with shell=True."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(returncode=0, stdout="file1 file2", stderr="")

        executor = HostCommandExecutor(mock_ctx)
        _ = executor.execute("ls *.txt", shell=True)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("shell") is True

    @patch("subprocess.run")
    def test_execute_empty_command(self, mock_run):
        """Test executing with empty command."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        executor = HostCommandExecutor(mock_ctx)
        results = executor.execute()

        assert results == []
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_execute_command_as_string(self, mock_run):
        """Test executing command given as string."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        executor = HostCommandExecutor(mock_ctx)
        results = executor.execute("echo test")

        # String commands might be split or passed with shell=True
        assert len(results) == 1
        assert results[0].exit_code == 0
