"""Executes commands on the host via subprocess."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from minitrino.ansi import strip_ansi
from minitrino.core.errors import MinitrinoError

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext

from minitrino.core.exec.result import CommandResult


class HostCommandExecutor:
    """Executes commands on the host via subprocess."""

    def __init__(self, ctx: MinitrinoContext) -> None:
        self._ctx = ctx

    def execute(
        self,
        command: list[str],
        interactive: bool = False,
        **kwargs: Any,
    ) -> CommandResult:
        """Execute a command on the host via subprocess."""
        self._ctx.logger.debug(f"Executing command on host:\n{command}")
        start_time = time.monotonic()
        output = ""
        rc = -1
        last_e: Exception | None = None
        error: MinitrinoError | None = None
        try:
            if interactive:
                env = self._handle_env(kwargs.get("environment", {}))
                completed = subprocess.run(
                    command,
                    env=env,
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                rc = completed.returncode
            else:
                env = self._handle_env(kwargs.get("environment", {}))
                process = subprocess.Popen(
                    command,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                )

                def kill_proc_on_signal(signum, frame):
                    self._ctx.logger.warn(f"Killing subprocess on signal {signum}")
                    process.terminate()

                old_sigint = signal.signal(signal.SIGINT, kill_proc_on_signal)
                old_sigterm = signal.signal(signal.SIGTERM, kill_proc_on_signal)
                try:
                    if not kwargs.get("suppress_output", False):
                        started_stream = False
                        if process.stdout is not None:
                            for line in self._iter_lines(process):
                                clean_line = strip_ansi(line)
                                if not started_stream:
                                    self._ctx.logger.debug("Command Output:")
                                    started_stream = True
                                self._ctx.logger.debug(clean_line)
                                output += clean_line
                    else:
                        outs, _ = process.communicate()
                        output = outs
                        rc = process.returncode
                    rc = process.wait()
                finally:
                    signal.signal(signal.SIGINT, old_sigint)
                    signal.signal(signal.SIGTERM, old_sigterm)
        except Exception as e:
            last_e = e
            rc = -1
        if rc != 0:
            error = MinitrinoError(
                f"Failed to execute command on host:\n{command}\n"
                f"Exit code: {rc}\nCommand output: {output}",
                last_e,
            )
        if kwargs.get("trigger_error", True) and isinstance(error, MinitrinoError):
            raise error

        duration = time.monotonic() - start_time
        return CommandResult(
            command,
            output=strip_ansi(output),
            exit_code=rc,
            duration=duration,
            error=error,
        )

    def stream_execute(
        self,
        command: list[str],
        interactive: bool = False,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Stream output lines from a subprocess."""
        if interactive:
            raise NotImplementedError("Interactive streaming not supported.")

        env = self._handle_env(kwargs.get("environment", {}))

        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        try:
            suppress = bool(kwargs.get("suppress_output", False))
            if not suppress:
                self._ctx.logger.debug(f"Streaming command on host:\n{command}")
            if process.stdout is not None:
                for line in self._iter_lines(process):
                    clean_line = strip_ansi(line)
                    if not suppress:
                        self._ctx.logger.debug(clean_line)
                    yield clean_line
            process.wait()
        finally:
            process.stdout and process.stdout.close()

    def _handle_env(self, env_override: dict[str, Any] | None = None) -> dict[str, str]:
        """Handle environment variables for subprocess execution.

        Parameters
        ----------
        env_override : dict[str, Any], optional
            Environment variables to override or add to the current
            environment. Defaults to None.

        Returns
        -------
        dict[str, str]
            Complete environment dictionary for subprocess execution.
        """
        env = os.environ.copy()
        if env_override:
            env.update(env_override)
        return env

    def stream_execute_with_result(
        self,
        command: list[str],
        **kwargs: Any,
    ) -> tuple[Iterator[str], threading.Event, Callable[[], CommandResult]]:
        """Stream output lines from a subprocess with access to exit code.

        Returns a tuple of:
        - Iterator[str]: Yields output lines as they are produced
        - threading.Event: Signals when the process has completed
        - Callable[[], CommandResult]: Returns the final CommandResult

        This method enables fast failure detection by providing both streaming
        output and immediate access to process completion status and exit code.

        Parameters
        ----------
        command : list[str]
            The command to execute.
        **kwargs : Any
            Additional keyword arguments for subprocess execution.

        Returns
        -------
        Tuple[Iterator[str], threading.Event, Callable[[], CommandResult]]
            A tuple containing the output iterator, completion event, and
            result callable.
        """
        env = self._handle_env(kwargs.get("environment", {}))
        start_time = time.monotonic()
        output_lines: list[str] = []
        exit_code_holder: dict[str, int] = {"exit_code": -1}
        error_holder: dict[str, BaseException | None] = {"error": None}
        completion_event = threading.Event()

        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        def monitor_process() -> None:
            """Monitor process completion in a separate thread."""
            try:
                exit_code = process.wait()
                exit_code_holder["exit_code"] = exit_code
                if exit_code != 0:
                    error_holder["error"] = MinitrinoError(
                        f"Command failed with exit code {exit_code}"
                    )
            except Exception as e:
                exit_code_holder["exit_code"] = -1
                error_holder["error"] = e
            finally:
                completion_event.set()

        monitor_thread = threading.Thread(target=monitor_process, daemon=True)
        monitor_thread.start()

        def output_iterator() -> Iterator[str]:
            """Yield output lines from the process."""
            suppress = kwargs.get("suppress_output", False)
            try:
                if not suppress:
                    self._ctx.logger.debug(f"Streaming command on host:\n{command}")
                if process.stdout is not None:
                    for line in self._iter_lines(process):
                        clean_line = strip_ansi(line)
                        if not suppress:
                            self._ctx.logger.debug(clean_line)
                        output_lines.append(clean_line)
                        yield clean_line
            finally:
                if process.stdout:
                    process.stdout.close()
                monitor_thread.join(timeout=1)  # Wait briefly for exit code

        def get_result() -> CommandResult:
            """Get the final command result."""
            duration = time.monotonic() - start_time
            output = "".join(output_lines)
            return CommandResult(
                command=command,
                output=output,
                exit_code=exit_code_holder["exit_code"],
                duration=duration,
                error=error_holder["error"],
                process_handle=process,
                is_completed=completion_event.is_set(),
            )

        return output_iterator(), completion_event, get_result

    def _iter_lines(self, process: subprocess.Popen):
        """Iterate lines from a process.

        Parameters
        ----------
        process : subprocess.Popen
            The process to read lines from.

        Yields
        ------
        str
            Output lines from the process.
        """
        while True:
            if process.stdout is None:
                break
            line = process.stdout.readline()
            if line == "" and process.poll() is not None:
                break
            yield line
