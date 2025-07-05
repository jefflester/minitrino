"""Executes commands on the host via subprocess."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any, Iterator

from minitrino import utils
from minitrino.core.errors import MinitrinoError

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext

from minitrino.core.exec.result import CommandResult


class HostCommandExecutor:
    """Executes commands on the host via subprocess."""

    def __init__(self, ctx: "MinitrinoContext") -> None:
        self._ctx = ctx

    def execute(
        self,
        command: list[str],
        interactive: bool = False,
        **kwargs: Any,
    ) -> "CommandResult":
        """Execute a command on the host via subprocess."""
        self._ctx.logger.debug(f"Executing command on host:\n{command}")
        start_time = time.monotonic()
        output = ""
        rc = -1
        last_e: Exception | None = None
        error: MinitrinoError | None = None
        try:
            if interactive:
                env = os.environ.copy()
                env_override = kwargs.get("environment")
                if env_override:
                    env.update(env_override)
                completed = subprocess.run(
                    command,
                    env=env,
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                rc = completed.returncode
            else:
                env = os.environ.copy()
                env_override = kwargs.get("environment")
                if env_override:
                    env.update(env_override)
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
                                clean_line = utils.strip_ansi(line)
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
            output=utils.strip_ansi(output),
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
        process = subprocess.Popen(
            command,
            env=kwargs.get("environment", {}),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        try:
            suppress = False if not kwargs.get("suppress_output", False) else True
            if not suppress:
                self._ctx.logger.debug(f"Streaming command on host:\n{command}")
            if process.stdout is not None:
                for line in self._iter_lines(process):
                    clean_line = utils.strip_ansi(line)
                    if not suppress:
                        self._ctx.logger.debug(clean_line)
                    yield clean_line
            process.wait()
        finally:
            process.stdout and process.stdout.close()

    def _iter_lines(self, process: subprocess.Popen):
        """
        Iterate lines from a process.

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
