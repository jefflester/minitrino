"""Unit tests for container command execution.

Tests the ContainerCommandExecutor class for executing commands in Docker containers.
"""

from unittest.mock import Mock

import pytest

from minitrino.core.errors import MinitrinoError
from minitrino.core.exec.container import ContainerCommandExecutor


class TestContainerCommandExecutor:
    """Test suite for ContainerCommandExecutor."""

    def test_executor_initialization(self):
        """Test creating a ContainerCommandExecutor."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        executor = ContainerCommandExecutor(mock_ctx)

        assert executor._ctx == mock_ctx

    def test_execute_in_container(self):
        """Test executing command in a container."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (0, b"container output")

        executor = ContainerCommandExecutor(mock_ctx)
        results = executor.execute(["echo", "hello"], container=mock_container)

        assert len(results) == 1
        assert results[0].exit_code == 0
        assert (
            "container output" in results[0].output
            or results[0].output == "container output"
        )
        mock_container.exec_run.assert_called_once()

    def test_execute_without_container(self):
        """Test that executing without container raises error."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()

        executor = ContainerCommandExecutor(mock_ctx)

        with pytest.raises((MinitrinoError, ValueError)):
            executor.execute(["echo", "hello"])

    def test_execute_with_user(self):
        """Test executing command as specific user."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (0, b"testuser")

        executor = ContainerCommandExecutor(mock_ctx)
        _ = executor.execute(["whoami"], container=mock_container, user="testuser")

        call_kwargs = mock_container.exec_run.call_args[1]
        assert call_kwargs.get("user") == "testuser"

    def test_execute_with_environment(self):
        """Test executing with environment variables."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (0, b"VALUE")

        executor = ContainerCommandExecutor(mock_ctx)
        _ = executor.execute(
            ["printenv", "MY_VAR"],
            container=mock_container,
            environment={"MY_VAR": "VALUE"},
        )

        call_kwargs = mock_container.exec_run.call_args[1]
        assert call_kwargs.get("environment") == {"MY_VAR": "VALUE"}

    def test_execute_multiple_commands(self):
        """Test executing multiple commands in sequence."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.side_effect = [(0, b"output1"), (0, b"output2")]

        executor = ContainerCommandExecutor(mock_ctx)
        results = executor.execute(
            ["echo", "one"], ["echo", "two"], container=mock_container
        )

        assert len(results) == 2
        assert "output1" in results[0].output or results[0].output == "output1"
        assert "output2" in results[1].output or results[1].output == "output2"
        assert mock_container.exec_run.call_count == 2

    def test_execute_with_error(self):
        """Test executing command that fails."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (1, b"Command failed")

        executor = ContainerCommandExecutor(mock_ctx)
        results = executor.execute(["false"], container=mock_container)

        assert results[0].exit_code == 1
        assert (
            "Command failed" in results[0].output
            or results[0].error == "Command failed"
        )

    def test_execute_with_trigger_error(self):
        """Test that trigger_error raises on non-zero exit."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (1, b"Error")

        executor = ContainerCommandExecutor(mock_ctx)

        with pytest.raises(MinitrinoError):
            executor.execute(["false"], container=mock_container, trigger_error=True)

    def test_execute_interactive(self):
        """Test executing in interactive mode."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()

        # Mock the API client and socket
        mock_api = Mock()
        mock_container.client.api = mock_api
        mock_socket = Mock()
        mock_api.exec_create.return_value = {"Id": "exec123"}
        mock_api.exec_start.return_value = mock_socket
        mock_api.exec_inspect.return_value = {"ExitCode": 0}

        executor = ContainerCommandExecutor(mock_ctx)
        _ = executor.execute(["bash"], container=mock_container, interactive=True)

        # Should use Docker API for interactive mode
        mock_api.exec_create.assert_called_once()
        create_kwargs = mock_api.exec_create.call_args[1]
        assert create_kwargs.get("tty") is True
        assert create_kwargs.get("stdin") is True

    def test_execute_with_workdir(self):
        """Test executing with working directory."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (0, b"/app")

        executor = ContainerCommandExecutor(mock_ctx)
        _ = executor.execute(["pwd"], container=mock_container, workdir="/app")

        call_kwargs = mock_container.exec_run.call_args[1]
        assert call_kwargs.get("workdir") == "/app"

    def test_execute_with_detach(self):
        """Test executing in detached mode."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_exec_instance = Mock()
        mock_container.exec_run.return_value = mock_exec_instance

        executor = ContainerCommandExecutor(mock_ctx)
        _ = executor.execute(["sleep", "10"], container=mock_container, detach=True)

        call_kwargs = mock_container.exec_run.call_args[1]
        assert call_kwargs.get("detach") is True

    def test_execute_with_suppress_output(self):
        """Test executing with output suppression."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (0, b"output")

        executor = ContainerCommandExecutor(mock_ctx)
        results = executor.execute(
            ["echo", "test"], container=mock_container, suppress_output=True
        )

        # Output should be captured but not logged
        assert "output" in results[0].output or results[0].output == "output"
        # Logger shouldn't be called for output
        mock_ctx.logger.msg.assert_not_called()

    def test_execute_with_stream(self):
        """Test executing with stream output."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()

        # Mock streaming output
        mock_container.exec_run.return_value = (0, [b"line1\n", b"line2\n", b"line3\n"])

        executor = ContainerCommandExecutor(mock_ctx)
        _ = executor.execute(["cat", "file.txt"], container=mock_container, stream=True)

        call_kwargs = mock_container.exec_run.call_args[1]
        assert call_kwargs.get("stream") is True

    def test_execute_command_as_string(self):
        """Test executing command given as string."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (0, b"output")

        executor = ContainerCommandExecutor(mock_ctx)
        results = executor.execute("echo test", container=mock_container)

        # String should be passed to exec_run
        assert len(results) == 1
        assert results[0].exit_code == 0

    def test_execute_with_privileged(self):
        """Test executing with privileged mode."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()
        mock_container.exec_run.return_value = (0, b"output")

        executor = ContainerCommandExecutor(mock_ctx)
        _ = executor.execute(["mount"], container=mock_container, privileged=True)

        call_kwargs = mock_container.exec_run.call_args[1]
        assert call_kwargs.get("privileged") is True

    def test_execute_empty_command(self):
        """Test executing with empty command."""
        mock_ctx = Mock()
        mock_ctx.logger = Mock()
        mock_container = Mock()

        executor = ContainerCommandExecutor(mock_ctx)
        results = executor.execute(container=mock_container)

        assert results == []
        mock_container.exec_run.assert_not_called()
