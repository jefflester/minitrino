"""Spinner logging utility."""

from __future__ import annotations

import itertools
import logging
import sys
import threading
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Optional

from minitrino.core.logging.levels import LogLevel
from minitrino.shutdown import shutdown_event

if TYPE_CHECKING:
    from minitrino.core.logging.logger import MinitrinoLogger


class LogBuffer:
    """
    Helper class for buffering and replaying log messages.

    Buffers messages as (msg, is_spinner_artifact, stream) tuples and
    can flush them to the appropriate output stream.
    """

    def __init__(self) -> None:
        self.buffer: list[tuple[str, bool, str]] = []

    def append(self, msg: str, is_spinner_artifact: bool, stream: str) -> None:
        """Append a log message to the buffer."""
        self.buffer.append((msg, is_spinner_artifact, stream))

    def flush(self) -> None:
        """Flush the buffer to the appropriate output stream."""
        for msg, is_spinner_artifact, stream in self.buffer:
            if not is_spinner_artifact:
                print(msg, file=(sys.stderr if stream == "stderr" else sys.stdout))
        self.buffer.clear()


class _SpinnerThread(threading.Thread):
    """
    Helper thread for displaying spinner animation.

    Parameters
    ----------
    prefix : str
        Prefix to display before spinner.
    message : str
        Message to display alongside spinner.
    output_lock : threading.RLock
        Lock to synchronize output.
    spinner_done : threading.Event
        Event to signal spinner completion.
    log_buffer : LogBuffer | None
        Optional buffer for spinner artifacts.
    """

    def __init__(
        self,
        prefix: str,
        message: str,
        output_lock: threading.RLock,
        spinner_done: threading.Event,
        log_buffer: Optional[LogBuffer] = None,
    ) -> None:
        super().__init__(daemon=True)
        self.prefix = prefix
        self.message = message
        self.output_lock = output_lock
        self.spinner_done = spinner_done
        self.log_buffer = log_buffer

    def run(self) -> None:
        """Run the spinner thread."""
        for c in itertools.cycle(r"\|/-"):
            if self.spinner_done.is_set() or shutdown_event.is_set():
                if shutdown_event.is_set():
                    self.spinner_done.set()
                break
            acquired = self.output_lock.acquire(blocking=False)
            if acquired:
                try:
                    spinner_msg = f"\r{self.prefix}{self.message} {c}"
                    sys.stdout.write(spinner_msg)
                    sys.stdout.flush()
                    if self.log_buffer is not None:
                        self.log_buffer.append(spinner_msg, True, "stdout")
                finally:
                    self.output_lock.release()
            time.sleep(0.1)


class Spinner:
    """
    Spinner logging utility.

    Displays a spinner while a task is in progress.

    The spinner only appears if:

    - stdout is a TTY
    - log level is not DEBUG

    Parameters
    ----------
    logger : MinitrinoLogger
        The logger instance to use for spinner state.
    log_sink : Callable[[str, str, bool], None] | None
        The log sink to use for spinner state.
    always_verbose : bool
        If True, disables spinner and always streams logs directly.
    """

    def __init__(
        self,
        logger: MinitrinoLogger,
        log_sink: Optional[Callable[[str, str, bool], None]] = None,
        always_verbose: bool = False,
    ) -> None:
        self.logger: MinitrinoLogger = logger
        self.log_sink: Optional[Callable[[str, str, bool], None]] = log_sink
        self.spinner_active = threading.local()
        self.spinner_active.value = False

        self.output_lock = threading.RLock()
        self._spinner_thread: Optional[threading.Thread] = None
        self.always_verbose = always_verbose

    @contextmanager
    def spinner(self, message: str = ""):
        """
        Display a spinner while a task is in progress.

        If not a TTY or logging to a file, disables spinner and
        buffering.

        Parameters
        ----------
        message : str
            Message to display alongside the spinner.
        """
        if self.always_verbose or self.logger._log_level == LogLevel.DEBUG:
            yield
            return
        if not sys.stdout.isatty():
            yield
            return
        if any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            yield
            return

        log_buffer = LogBuffer()
        try:
            self._set_spinner_active(True)
            spinner_done = self._start_spinner(message, log_buffer)
            try:
                yield
            finally:
                self._set_spinner_active(False)
                self._stop_spinner(spinner_done)
        finally:
            self._clear_spinner_line()
            sys.stdout.flush()
            log_buffer.flush()

    def _start_spinner(
        self,
        message: str = "",
        log_buffer: Optional[LogBuffer] = None,
    ) -> threading.Event:
        """Start the spinner animation."""
        spinner_done = threading.Event()
        prefix = self.logger.styled_prefix()
        self._spinner_thread = _SpinnerThread(
            prefix=prefix,
            message=message,
            output_lock=self.output_lock,
            spinner_done=spinner_done,
            log_buffer=log_buffer,
        )
        self._spinner_thread.start()
        return spinner_done

    def _stop_spinner(self, spinner_done: threading.Event, delay: float = 0.1) -> None:
        """
        Stop the spinner and clear the terminal line.

        Parameters
        ----------
        spinner_done : threading.Event
            The event returned by _start_spinner.
        delay : float
            Time to wait for the spinner thread to exit.
        """
        spinner_done.set()
        if self._spinner_thread is not None:
            self._spinner_thread.join(timeout=delay)
        with self.output_lock:
            sys.stdout.write("\033[2K\r")  # Only clear, no newline
            sys.stdout.flush()

    def _set_spinner_active(self, active: bool):
        self.spinner_active.value = active

    def _is_spinner_active(self) -> bool:
        return getattr(self.spinner_active, "value", False)

    def _clear_spinner_line(self):
        # Used by SpinnerAwareHandler; always clear if TTY
        if sys.stdout.isatty():
            with self.output_lock:
                sys.stdout.write("\033[2K\r")
                sys.stdout.flush()
