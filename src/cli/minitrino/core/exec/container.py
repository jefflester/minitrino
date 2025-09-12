"""Execute commands inside Docker containers."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Generator, Iterator, Optional, Tuple

from minitrino.core.docker.wrappers import MinitrinoContainer
from minitrino.core.errors import MinitrinoError
from minitrino.core.exec.result import CommandResult
from minitrino.core.exec.utils import detect_container_shell

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class ContainerCommandExecutor:
    """Execute commands inside containers."""

    def __init__(self, ctx: "MinitrinoContext") -> None:
        self._ctx = ctx
        self.shell = None

    def execute(
        self,
        command: list[str],
        **kwargs: Any,
    ) -> "CommandResult":
        """Execute a command inside a container."""
        container: MinitrinoContainer = kwargs.get("container", None)
        if not container:
            raise ValueError(
                "Container parameter is required for ContainerCommandExecutor"
            )
        user: str = kwargs.get("user", "root")
        self._set_shell(container, user)
        docker_cmd = [self.shell, "-c", " ".join(command)]
        self._ctx.logger.debug(
            f"Executing command in container '{container.name}':\n{docker_cmd}"
        )
        start_time = time.monotonic()
        output = ""
        rc = -1
        error: MinitrinoError | None = None
        last_e: Exception | None = None
        try:
            exec_handler = self._ctx.api_client.exec_create(
                container.name,
                cmd=docker_cmd,
                environment=kwargs.get("environment", None),
                privileged=True,
                user=user,
            )
            output_generator: Generator = self._ctx.api_client.exec_start(
                exec_handler, stream=True
            )
            for line in self._buffer_exec_output_lines(
                output_generator, kwargs.get("suppress_output", False)
            ):
                output += line
            rc = self._ctx.api_client.exec_inspect(exec_handler["Id"]).get("ExitCode")
            if rc in [126, 127]:
                self._ctx.logger.warn(
                    f"The command '{docker_cmd}' exited with a {rc} code which "
                    f"typically means an executable is not accessible or installed. "
                    f"Does this image have all required dependencies installed?\n"
                    f"Command output: {output}"
                )
        except Exception as e:
            last_e = e
            rc = -1
        if rc != 0:
            error = MinitrinoError(
                f"Failed to execute command in container "
                f"{container.name}:\n{docker_cmd}\n"
                f"Exit code: {rc}\nCommand output: {output}",
                last_e,
            )
        if kwargs.get("trigger_error", True) and isinstance(error, MinitrinoError):
            raise error

        duration = time.monotonic() - start_time
        return CommandResult(
            docker_cmd,
            output=output,
            exit_code=rc,
            duration=duration,
            error=error,
        )

    def stream_execute(
        self,
        command: list[str],
        **kwargs: Any,
    ) -> Iterator[str]:
        """Stream output from a command inside a container."""
        container: MinitrinoContainer = kwargs.get("container", None)
        if not container:
            raise ValueError(
                "Container parameter is required for ContainerCommandExecutor"
            )
        user: str = kwargs.get("user", "root")
        self._set_shell(container, user)
        docker_cmd = [self.shell, "-c", " ".join(command)]
        self._ctx.logger.debug(
            f"Streaming command '{docker_cmd}' in container '{container.name}'"
        )
        exec_handler = self._ctx.api_client.exec_create(
            container.name,
            cmd=docker_cmd,
            environment=kwargs.get("environment", None),
            privileged=True,
            user=user,
        )
        output_generator: Generator = self._ctx.api_client.exec_start(
            exec_handler, stream=True
        )
        for line in self._buffer_exec_output_lines(
            output_generator, kwargs.get("suppress_output", False)
        ):
            self._ctx.logger.debug(line)
            yield line

    def stream_execute_with_result(
        self,
        command: list[str],
        **kwargs: Any,
    ) -> Tuple[Iterator[str], threading.Event, Callable[[], CommandResult]]:
        """
        Stream output from a container command with access to exit code.

        Returns a tuple of:
        - Iterator[str]: Yields output lines as they are produced
        - threading.Event: Signals when the command has completed
        - Callable[[], CommandResult]: Returns the final CommandResult

        This method enables fast failure detection by providing both streaming
        output and immediate access to command completion status and exit code.

        Parameters
        ----------
        command : list[str]
            The command to execute.
        **kwargs : Any
            Additional keyword arguments including container, user, etc.

        Returns
        -------
        Tuple[Iterator[str], threading.Event, Callable[[], CommandResult]]
            A tuple containing the output iterator, completion event, and
            result callable.
        """
        container: MinitrinoContainer = kwargs.get("container", None)
        if not container:
            raise ValueError(
                "Container parameter is required for ContainerCommandExecutor"
            )
        user: str = kwargs.get("user", "root")
        self._set_shell(container, user)
        docker_cmd = [self.shell, "-c", " ".join(command)]

        start_time = time.monotonic()
        output_lines: list[str] = []
        exit_code_holder: dict[str, int] = {"exit_code": -1}
        error_holder: dict[str, Optional[BaseException]] = {"error": None}
        exec_id_holder: dict[str, Optional[str]] = {"exec_id": None}
        completion_event = threading.Event()

        self._ctx.logger.debug(
            f"Streaming command '{docker_cmd}' in container '{container.name}' "
            f"with result tracking"
        )

        try:
            exec_handler = self._ctx.api_client.exec_create(
                container.name,
                cmd=docker_cmd,
                environment=kwargs.get("environment", None),
                privileged=True,
                user=user,
            )
            exec_id_holder["exec_id"] = exec_handler["Id"]

            output_generator: Generator = self._ctx.api_client.exec_start(
                exec_handler, stream=True
            )

            def monitor_exec() -> None:
                """Monitor exec completion in a separate thread."""
                try:
                    # Poll exec_inspect periodically to check if command completed
                    while not completion_event.is_set():
                        try:
                            exec_info = self._ctx.api_client.exec_inspect(
                                exec_id_holder["exec_id"]
                            )
                            if not exec_info.get("Running", True):
                                exit_code = exec_info.get("ExitCode", -1)
                                exit_code_holder["exit_code"] = exit_code
                                if exit_code != 0:
                                    error_holder["error"] = MinitrinoError(
                                        f"Command failed with exit code {exit_code}"
                                    )
                                completion_event.set()
                                break
                        except Exception:
                            pass  # Ignore errors during polling
                        threading.Event().wait(0.1)  # Small delay between polls
                except Exception as e:
                    exit_code_holder["exit_code"] = -1
                    error_holder["error"] = e
                    completion_event.set()

            monitor_thread = threading.Thread(target=monitor_exec, daemon=True)
            monitor_thread.start()

            def output_iterator() -> Iterator[str]:
                """Yield output lines from the container command."""
                suppress = kwargs.get("suppress_output", False)
                try:
                    for line in self._buffer_exec_output_lines(
                        output_generator, False  # Always get all lines
                    ):
                        output_lines.append(line)
                        if not suppress:
                            self._ctx.logger.debug(line)
                        yield line
                finally:
                    # Signal completion if not already done
                    if not completion_event.is_set():
                        # Final check for exit code
                        try:
                            exec_info = self._ctx.api_client.exec_inspect(
                                exec_id_holder["exec_id"]
                            )
                            exit_code_holder["exit_code"] = exec_info.get(
                                "ExitCode", -1
                            )
                        except Exception:
                            pass
                        completion_event.set()
                    monitor_thread.join(timeout=1)

            def get_result() -> CommandResult:
                """Get the final command result."""
                duration = time.monotonic() - start_time
                output = "".join(output_lines)

                # Final exit code check if not already set
                if exit_code_holder["exit_code"] == -1 and exec_id_holder["exec_id"]:
                    try:
                        exec_info = self._ctx.api_client.exec_inspect(
                            exec_id_holder["exec_id"]
                        )
                        exit_code_holder["exit_code"] = exec_info.get("ExitCode", -1)
                    except Exception:
                        pass

                return CommandResult(
                    command=docker_cmd,
                    output=output,
                    exit_code=exit_code_holder["exit_code"],
                    duration=duration,
                    error=error_holder["error"],
                    process_handle=exec_id_holder["exec_id"],
                    is_completed=completion_event.is_set(),
                )

            return output_iterator(), completion_event, get_result

        except Exception as e:
            # If we fail to even start the exec, return error immediately
            completion_event.set()
            error_holder["error"] = e

            def empty_iterator() -> Iterator[str]:
                return
                yield  # Make it a generator

            def get_error_result() -> CommandResult:
                duration = time.monotonic() - start_time
                return CommandResult(
                    command=docker_cmd,
                    output="",
                    exit_code=-1,
                    duration=duration,
                    error=error_holder["error"],
                    is_completed=True,
                )

            return empty_iterator(), completion_event, get_error_result

    def _set_shell(self, container: MinitrinoContainer, user: str = "root") -> None:
        """Set the shell for the container."""
        if self.shell is not None:
            return
        self.shell = detect_container_shell(self._ctx, container, user)

    def _buffer_exec_output_lines(
        self, output_generator: Generator[bytes, None, None], suppress_output: bool
    ):
        """
        Buffer Docker exec_start output chunks into lines.

        Yields lines as they are completed.

        Parameters
        ----------
        output_generator : generator
            Generator yielding bytes from Docker exec_start.
        suppress_output : bool
            If True, do not log output lines.

        Yields
        ------
        str
            Output lines as they are completed (including trailing newlines).
        """
        started_stream = False
        full_line = ""
        for chunk in output_generator:
            decoded = chunk.decode(errors="replace")
            lines = decoded.split("\n")
            for i, part in enumerate(lines):
                if i == 0:
                    full_line += part
                else:
                    if not suppress_output and (started_stream or full_line):
                        yield full_line + "\n"
                    full_line = part
                    started_stream = True
        if full_line and (started_stream or not suppress_output):
            yield full_line
