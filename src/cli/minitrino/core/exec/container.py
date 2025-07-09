"""Execute commands inside Docker containers."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Generator, Iterator

from minitrino import utils
from minitrino.core.docker.wrappers import MinitrinoContainer
from minitrino.core.errors import MinitrinoError
from minitrino.core.exec.utils import detect_container_shell

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext
    from minitrino.core.exec.result import CommandResult


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
