r"""Watchdog for detecting hung test processes.

Monitors stdout/stderr for write activity. If no output is produced for
a configurable duration (default: 10 minutes), dumps diagnostic info
(``docker ps``, container logs) and force-exits the process.

Activated automatically for all pytest test suites via the session-scoped
``_watchdog`` fixture in ``src/tests/conftest.py``. Configure via the
``--watchdog-timeout`` pytest option or ``WATCHDOG_TIMEOUT`` env var.
"""

import os
import subprocess
import sys
import threading
from time import monotonic, sleep
from typing import IO, Any, TextIO

from tests import common


class OutputMonitor:
    """Wrap a text stream to track the last time a write occurred.

    Delegates all attribute access to the wrapped stream so it remains a drop-in
    replacement for sys.stdout / sys.stderr.
    """

    def __init__(self, wrapped: TextIO, watchdog: "Watchdog") -> None:
        self._wrapped = wrapped
        self._watchdog = watchdog

    def write(self, s: str) -> int:
        """Write to the wrapped stream and ping the watchdog."""
        self._watchdog.ping()
        return self._wrapped.write(s)

    def flush(self) -> None:
        """Flush the wrapped stream."""
        self._wrapped.flush()

    def fileno(self) -> int:
        """Return the file descriptor of the wrapped stream."""
        return self._wrapped.fileno()

    def isatty(self) -> bool:
        """Return whether the wrapped stream is a TTY."""
        return self._wrapped.isatty()

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attribute access to the wrapped stream."""
        return getattr(self._wrapped, name)


class Watchdog:
    """Daemon thread that force-exits on prolonged output silence.

    Parameters
    ----------
    timeout : int
        Seconds of stdout/stderr silence before triggering. Default 600.
    poll_interval : int
        How often (seconds) the watchdog checks for silence. Default 30.
    """

    def __init__(self, timeout: int = 600, poll_interval: int = 30) -> None:
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._last_activity = monotonic()
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None
        self._original_stdout: TextIO | None = None
        self._original_stderr: TextIO | None = None

    def ping(self) -> None:
        """Record output activity (called by OutputMonitor on every write)."""
        with self._lock:
            self._last_activity = monotonic()

    def start(self) -> None:
        """Install output monitors and start the watchdog thread."""
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = OutputMonitor(self._original_stdout, self)  # type: ignore[assignment]
        sys.stderr = OutputMonitor(self._original_stderr, self)  # type: ignore[assignment]

        self._thread = threading.Thread(target=self._run, daemon=True, name="watchdog")
        self._thread.start()

    def stop(self) -> None:
        """Stop the watchdog and restore original streams."""
        self._stopped.set()
        if self._original_stdout is not None:
            sys.stdout = self._original_stdout
        if self._original_stderr is not None:
            sys.stderr = self._original_stderr

    def _seconds_since_activity(self) -> float:
        with self._lock:
            return monotonic() - self._last_activity

    def _run(self) -> None:
        while not self._stopped.is_set():
            sleep(self.poll_interval)
            idle = self._seconds_since_activity()
            if idle >= self.timeout:
                self._on_timeout(idle)
                return

    def _on_timeout(self, idle_seconds: float) -> None:
        """Dump diagnostics and force-exit."""
        out: IO[str] = self._original_stdout or sys.stdout
        sep = "=" * 72

        out.write(f"\n{sep}\n")
        out.write(
            f"WATCHDOG: No output for {idle_seconds:.0f}s "
            f"(threshold: {self.timeout}s). Dumping diagnostics.\n"
        )
        out.write(f"{sep}\n\n")
        out.flush()

        self._dump_docker_ps(out)
        self._dump_container_logs(out)

        out.write(f"\n{sep}\n")
        out.write("WATCHDOG: Force-exiting process.\n")
        out.write(f"{sep}\n")
        out.flush()

        os._exit(1)

    @staticmethod
    def _dump_docker_ps(out: IO[str]) -> None:
        out.write("--- docker ps -a ---\n")
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--format",
                    "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            out.write(result.stdout or "(no output)\n")
            if result.stderr:
                out.write(result.stderr)
        except Exception as e:
            out.write(f"(failed: {e})\n")
        out.write("\n")
        out.flush()

    @staticmethod
    def _dump_container_logs(out: IO[str]) -> None:
        out.write("--- container logs ---\n")
        try:
            containers = common.get_containers(all=True)
            for container in containers:
                out.write(f"\n>> {container.name} <<\n")
                try:
                    logs = container.logs(tail=200).decode("utf-8", errors="replace")
                    out.write(logs if logs.strip() else "(empty)\n")
                except Exception as e:
                    out.write(f"(failed to get logs: {e})\n")
                out.write("\n")
        except Exception as e:
            out.write(f"(failed to list containers: {e})\n")
        out.flush()
