"""Unit tests for command execution dispatcher.

Tests the CommandExecutor class which dispatches to host or container executors.
"""

from unittest.mock import Mock, patch

from minitrino.core.exec.cmd import CommandExecutor
from minitrino.core.exec.result import CommandResult


class TestCommandExecutor:
    """Test suite for CommandExecutor dispatcher."""

    def test_executor_initialization(self):
        """Test creating a CommandExecutor."""
        mock_ctx = Mock()

        executor = CommandExecutor(mock_ctx)

        assert executor._ctx == mock_ctx

    @patch("minitrino.core.exec.cmd.HostCommandExecutor")
    def test_execute_on_host(self, mock_host_executor_class):
        """Test executing commands on the host."""
        mock_ctx = Mock()
        mock_host_executor = Mock()
        mock_host_executor_class.return_value = mock_host_executor
        mock_host_executor.execute.return_value = CommandResult(
            exit_code=0,
            output="success",
            error="",
            command=["echo", "hello"],
            duration=0.1,
        )

        executor = CommandExecutor(mock_ctx)
        results = executor.execute(["echo", "hello"])

        mock_host_executor_class.assert_called_once_with(mock_ctx)
        mock_host_executor.execute.assert_called_once()
        assert len(results) == 1
        assert results[0].exit_code == 0
        assert results[0].output == "success"

    @patch("minitrino.core.exec.cmd.ContainerCommandExecutor")
    def test_execute_in_container(self, mock_container_executor_class):
        """Test executing commands in a container."""
        mock_ctx = Mock()
        mock_container = Mock()
        mock_container_executor = Mock()
        mock_container_executor_class.return_value = mock_container_executor
        mock_container_executor.execute.return_value = CommandResult(
            exit_code=0,
            output="container output",
            error="",
            command=["ls", "-la"],
            duration=0.1,
        )

        executor = CommandExecutor(mock_ctx)
        results = executor.execute(["ls", "-la"], container=mock_container)

        mock_container_executor_class.assert_called_once_with(mock_ctx)
        mock_container_executor.execute.assert_called_once()
        assert len(results) == 1
        assert results[0].exit_code == 0
        assert results[0].output == "container output"

    @patch("minitrino.core.exec.cmd.HostCommandExecutor")
    def test_execute_multiple_commands(self, mock_host_executor_class):
        """Test executing multiple commands."""
        mock_ctx = Mock()
        mock_host_executor = Mock()
        mock_host_executor_class.return_value = mock_host_executor
        # Mock side_effect to return different results for each call
        mock_host_executor.execute.side_effect = [
            CommandResult(
                exit_code=0,
                output="output1",
                error="",
                command=["echo", "one"],
                duration=0.1,
            ),
            CommandResult(
                exit_code=0,
                output="output2",
                error="",
                command=["echo", "two"],
                duration=0.1,
            ),
        ]

        executor = CommandExecutor(mock_ctx)
        results = executor.execute(["echo", "one"], ["echo", "two"])

        assert len(results) == 2
        assert results[0].output == "output1"
        assert results[1].output == "output2"

    @patch("minitrino.core.exec.cmd.HostCommandExecutor")
    def test_execute_with_error(self, mock_host_executor_class):
        """Test executing command that fails."""
        mock_ctx = Mock()
        mock_host_executor = Mock()
        mock_host_executor_class.return_value = mock_host_executor
        mock_host_executor.execute.return_value = CommandResult(
            exit_code=1,
            output="",
            error="Command failed",
            command=["false"],
            duration=0.1,
        )

        executor = CommandExecutor(mock_ctx)
        results = executor.execute(["false"])

        assert len(results) == 1
        assert results[0].exit_code == 1
        assert results[0].error == "Command failed"

    @patch("minitrino.core.exec.cmd.HostCommandExecutor")
    def test_execute_with_kwargs(self, mock_host_executor_class):
        """Test passing kwargs to the underlying executor."""
        mock_ctx = Mock()
        mock_host_executor = Mock()
        mock_host_executor_class.return_value = mock_host_executor
        mock_host_executor.execute.return_value = CommandResult(
            exit_code=0,
            output="output",
            error="",
            command=["echo", "test"],
            duration=0.1,
        )

        executor = CommandExecutor(mock_ctx)
        _ = executor.execute(
            ["echo", "test"],
            suppress_output=True,
            trigger_error=False,
            environment={"KEY": "value"},
        )

        # Verify kwargs were passed
        call_kwargs = mock_host_executor.execute.call_args[1]
        assert call_kwargs["suppress_output"] is True
        assert call_kwargs["trigger_error"] is False
        assert call_kwargs["environment"] == {"KEY": "value"}

    @patch("minitrino.core.exec.cmd.ContainerCommandExecutor")
    def test_execute_interactive_in_container(self, mock_container_executor_class):
        """Test executing interactive command in container."""
        mock_ctx = Mock()
        mock_container = Mock()
        mock_container_executor = Mock()
        mock_container_executor_class.return_value = mock_container_executor
        mock_container_executor.execute.return_value = CommandResult(
            exit_code=0, output="", error="", command=["bash"], duration=0.1
        )

        executor = CommandExecutor(mock_ctx)
        _ = executor.execute(["bash"], container=mock_container, interactive=True)

        call_kwargs = mock_container_executor.execute.call_args[1]
        # Container executor receives kwargs but 'interactive' is popped before passing
        assert call_kwargs["container"] == mock_container
        # 'interactive' is not passed to container executor (it's popped)

    @patch("minitrino.core.exec.cmd.HostCommandExecutor")
    def test_execute_with_user(self, mock_host_executor_class):
        """Test executing command with specific user."""
        mock_ctx = Mock()
        mock_host_executor = Mock()
        mock_host_executor_class.return_value = mock_host_executor
        mock_host_executor.execute.return_value = CommandResult(
            exit_code=0, output="", error="", command=["whoami"], duration=0.1
        )

        executor = CommandExecutor(mock_ctx)
        _ = executor.execute(["whoami"], user="testuser")

        call_kwargs = mock_host_executor.execute.call_args[1]
        assert call_kwargs["user"] == "testuser"

    def test_execute_stream_support(self):
        """Test that stream methods exist if supported."""
        mock_ctx = Mock()

        executor = CommandExecutor(mock_ctx)

        # Check if stream methods exist
        assert hasattr(executor, "execute") or hasattr(executor, "stream")

    @patch("minitrino.core.exec.cmd.HostCommandExecutor")
    def test_execute_empty_command_list(self, mock_host_executor_class):
        """Test executing with no commands."""
        mock_ctx = Mock()
        mock_host_executor = Mock()
        mock_host_executor_class.return_value = mock_host_executor
        mock_host_executor.execute.return_value = []

        executor = CommandExecutor(mock_ctx)
        results = executor.execute()

        assert results == []
