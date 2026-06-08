"""Watchdog for detecting hung pytest sessions.

Implemented as a pytest plugin: each pytest lifecycle event (collection,
test start, fixture setup/teardown, test report) pings the watchdog. If no
event fires for ``timeout`` seconds, the watchdog dumps diagnostics to
``sys.__stderr__`` (bypassing pytest capture) AND to a file under
``WATCHDOG_DIAG_FILE`` so the CI failure-diagnostics action can pick it up,
then force-exits the process with ``os._exit(1)``.

External callers (e.g. test helpers that invoke long-running subprocesses
between pytest events) can call ``watchdog.ping()`` to reset the silence
timer.

Configure via the ``--watchdog-timeout`` pytest option or the
``WATCHDOG_TIMEOUT`` env var (default 900s; set to 0 to disable).
"""

import os
import subprocess
import sys
import threading
from pathlib import Path
from time import monotonic, sleep
from typing import IO

import pytest

_watchdog: "Watchdog | None" = None

DIAGNOSTICS_FILE = Path(
    os.environ.get("WATCHDOG_DIAG_FILE", "/tmp/watchdog-diagnostics.txt")
)


def ping() -> None:
    """Reset the watchdog silence timer.

    No-op if the watchdog is disabled. Safe to call from any thread.
    Test helpers that invoke long-running subprocesses (e.g. ``minitrino
    provision``) should call this between pytest events to avoid a
    false-positive timeout.
    """
    if _watchdog is not None:
        _watchdog._ping()


class Watchdog:
    """Daemon thread that force-exits on prolonged pytest-event silence.

    Parameters
    ----------
    timeout : int
        Seconds of pytest-event silence before triggering. Default 900.
    poll_interval : int
        How often (seconds) the watchdog checks for silence. Default 30.
    """

    def __init__(self, timeout: int = 900, poll_interval: int = 30) -> None:
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._last_activity = monotonic()
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the watchdog thread."""
        self._thread = threading.Thread(target=self._run, daemon=True, name="watchdog")
        self._thread.start()

    def stop(self) -> None:
        """Stop the watchdog thread."""
        self._stopped.set()

    def _ping(self) -> None:
        with self._lock:
            self._last_activity = monotonic()

    def _seconds_since_activity(self) -> float:
        with self._lock:
            return monotonic() - self._last_activity

    def _run(self) -> None:
        while not self._stopped.is_set():
            sleep(self.poll_interval)
            if self._stopped.is_set():
                return
            idle = self._seconds_since_activity()
            if idle >= self.timeout:
                self._on_timeout(idle)
                return

    def _on_timeout(self, idle_seconds: float) -> None:
        """Dump diagnostics to stderr (and a file) and force-exit."""
        streams: list[IO[str]] = [sys.__stderr__]
        diag_file: IO[str] | None = None
        try:
            DIAGNOSTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            diag_file = open(DIAGNOSTICS_FILE, "w")
            streams.append(diag_file)
        except Exception:
            pass
        try:
            self._dump(streams, idle_seconds)
        finally:
            if diag_file is not None:
                try:
                    diag_file.close()
                except Exception:
                    pass
        os._exit(1)

    def _dump(self, streams: list[IO[str]], idle_seconds: float) -> None:
        sep = "=" * 72
        for s in streams:
            s.write(f"\n{sep}\n")
            s.write(
                f"WATCHDOG: No pytest activity for {idle_seconds:.0f}s "
                f"(threshold: {self.timeout}s). Dumping diagnostics.\n"
            )
            s.write(f"{sep}\n\n")
            s.flush()
        self._dump_docker_ps(streams)
        self._dump_container_logs(streams)
        for s in streams:
            s.write(f"\n{sep}\nWATCHDOG: Force-exiting process.\n{sep}\n")
            s.flush()

    @staticmethod
    def _dump_docker_ps(streams: list[IO[str]]) -> None:
        for s in streams:
            s.write("--- docker ps -a ---\n")
            s.flush()
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
            for s in streams:
                s.write(result.stdout or "(no output)\n")
                if result.stderr:
                    s.write(result.stderr)
                s.write("\n")
                s.flush()
        except Exception as e:
            for s in streams:
                s.write(f"(failed: {e})\n")
                s.flush()

    @staticmethod
    def _dump_container_logs(streams: list[IO[str]]) -> None:
        for s in streams:
            s.write("--- container logs ---\n")
            s.flush()
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            names = [n for n in (result.stdout or "").splitlines() if n.strip()]
        except Exception as e:
            for s in streams:
                s.write(f"(failed to list containers: {e})\n")
                s.flush()
            return
        for name in names:
            for s in streams:
                s.write(f"\n>> {name} <<\n")
                s.flush()
            try:
                log_result = subprocess.run(
                    ["docker", "logs", "--tail", "200", name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                text = (log_result.stdout or "") + (log_result.stderr or "")
                for s in streams:
                    s.write(text if text.strip() else "(empty)\n")
                    s.write("\n")
                    s.flush()
            except Exception as e:
                for s in streams:
                    s.write(f"(failed to get logs: {e})\n")
                    s.flush()


# ---------- pytest plugin hooks ----------


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the watchdog timeout option."""
    group = parser.getgroup("minitrino", "Minitrino shared options")
    group.addoption(
        "--watchdog-timeout",
        type=int,
        default=None,
        help="Seconds of pytest-event silence before force-exit "
        "(default: 900, env: WATCHDOG_TIMEOUT, 0 to disable).",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Start the watchdog before pytest's capture plugin matters."""
    global _watchdog
    opt = config.getoption("--watchdog-timeout")
    timeout = opt if opt is not None else int(os.environ.get("WATCHDOG_TIMEOUT", "900"))
    if timeout <= 0:
        return
    _watchdog = Watchdog(timeout=timeout)
    _watchdog.start()


def pytest_unconfigure(config: pytest.Config) -> None:
    """Stop the watchdog at session teardown."""
    global _watchdog
    if _watchdog is not None:
        _watchdog.stop()
        _watchdog = None


def pytest_collectstart(collector: pytest.Collector) -> None:  # noqa: ARG001
    ping()


def pytest_collection_modifyitems(  # noqa: ARG001
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    ping()


def pytest_runtest_logstart(  # noqa: ARG001
    nodeid: str, location: tuple[str, int | None, str]
) -> None:
    ping()


def pytest_runtest_logreport(report: pytest.TestReport) -> None:  # noqa: ARG001
    ping()


def pytest_runtest_logfinish(  # noqa: ARG001
    nodeid: str, location: tuple[str, int | None, str]
) -> None:
    ping()


def pytest_fixture_setup(  # noqa: ARG001
    fixturedef: pytest.FixtureDef, request: pytest.FixtureRequest
) -> None:
    ping()


def pytest_fixture_post_finalizer(  # noqa: ARG001
    fixturedef: pytest.FixtureDef, request: pytest.FixtureRequest
) -> None:
    ping()
