"""Log spinner utility for MinitrinoLogger."""

from __future__ import annotations

import itertools
import logging
import sys
import threading
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Optional

from minitrino.core.logging.utils import LogLevel

if TYPE_CHECKING:
    from minitrino.core.logging.logger import MinitrinoLogger


class Spinner:
    """
    Spinner logging utility.

    This class provides a context manager for displaying a spinner while
    a task is in progress. The spinner only appears if (1) stdout is a
    TTY, and (2) the log level is not DEBUG.

    Parameters
    ----------
    logger : MinitrinoLogger
        The logger instance to use for spinner state.
    log_sink : Callable[[str], None] | list[str] | None, optional
        The log sink to use for spinner state. If None, a new
        instance is created.

    Methods
    -------
    spinner(message="") :
        Display a spinner while a task is in progress.
    spinner_and_buffered_logs(message="") :
        Display a spinner while a task is in progress, and buffer the
        logs.
    """

    def __init__(
        self,
        logger: MinitrinoLogger,
        log_sink: Optional[Callable[[str], None] | list[str]] = None,
    ) -> None:
        self.logger: MinitrinoLogger = logger
        self.log_sink: Optional[Callable[[str], None] | list[str]] = log_sink
        self.spinner_active = threading.local()
        self.spinner_active.value = False
        self.output_lock = threading.Lock()
        self._spinner_thread: Optional[threading.Thread] = None

    @contextmanager
    def spinner(self, message: str = ""):
        """
        Display a spinner while a task is in progress.

        - If not a TTY or logging to a file, disables spinner/buffering.
        - Otherwise, buffers logs and prints them after spinner
          completes.

        Parameters
        ----------
        message : str
            Message to display alongside the spinner.
        """
        if self.logger._log_level == LogLevel.DEBUG:
            yield
            return
        if not sys.stdout.isatty():
            yield
            return
        if any(isinstance(h, logging.FileHandler) for h in self.logger.logger.handlers):
            yield
            return

        log_buffer: list[tuple[str, bool, str]] = (
            []
        )  # (msg, is_spinner_artifact, stream)
        original_handlers = list(self.logger.logger.handlers)
        for handler in original_handlers:
            self.logger.logger.removeHandler(handler)

        # Set log sink to buffer logs as (msg, False, stream)
        def buffer_sink(
            msg: str, stream: str = "stdout", is_spinner_artifact: bool = False
        ):
            log_buffer.append((msg, is_spinner_artifact, stream))

        self.logger.set_log_sink(buffer_sink)
        try:
            self._set_spinner_active(True)
            spinner_done = self._start_spinner(message, log_buffer)
            try:
                yield
            finally:
                self._set_spinner_active(False)
                self._stop_spinner(spinner_done)
        finally:
            self.logger.set_log_sink(None)
            for handler in original_handlers:
                self.logger.logger.addHandler(handler)
            self._clear_spinner_line()
            sys.stdout.flush()
            # Only print non-spinner logs to their original streams
            for msg, is_spinner_artifact, stream in log_buffer:
                if not is_spinner_artifact:
                    print(msg, file=(sys.stderr if stream == "stderr" else sys.stdout))

    def _start_spinner(
        self,
        message: str = "",
        log_buffer: Optional[list[tuple[str, bool, str]]] = None,
    ) -> threading.Event:
        """Start the spinner."""
        spinner_done = threading.Event()

        def spin():
            prefix = self.logger.styled_prefix()
            for c in itertools.cycle(r"\|/-"):
                if spinner_done.is_set():
                    break
                acquired = self.output_lock.acquire(blocking=False)
                if acquired:
                    try:
                        spinner_msg = f"\r{prefix}{message} {c}"
                        sys.stdout.write(spinner_msg)
                        sys.stdout.flush()
                        if log_buffer is not None:
                            log_buffer.append((spinner_msg, True, "stdout"))
                    finally:
                        self.output_lock.release()
                time.sleep(0.1)

        self._spinner_thread = threading.Thread(target=spin, daemon=True)
        self._spinner_thread.start()
        return spinner_done

    def _stop_spinner(self, spinner_done: threading.Event, delay: float = 0.1) -> None:
        """
        Stop the spinner and clear the terminal line.

        Parameters
        ----------
        spinner_done : threading.Event
            The event returned by spinner.
        delay : float, optional
            Time to wait for the spinner thread to exit, by default 0.1.
        """
        spinner_done.set()
        if self._spinner_thread is not None:
            self._spinner_thread.join(timeout=delay)
        with self.output_lock:
            sys.stdout.write("\033[2K\r")
            sys.stdout.flush()

    def _set_spinner_active(self, active: bool):
        self.spinner_active.value = active

    def _is_spinner_active(self) -> bool:
        return getattr(self.spinner_active, "value", False)

    def _clear_spinner_line(self):
        if self._is_spinner_active() and sys.stdout.isatty():
            with self.output_lock:
                sys.stdout.write("\033[2K\r")
                sys.stdout.flush()


class SpinnerAwareHandler(logging.StreamHandler):
    """Handler that clears the spinner line before emitting a record."""

    def __init__(self, spinner: Spinner):
        super().__init__()
        self.spinner = spinner

    def emit(self, record: logging.LogRecord):
        """Clear the spinner line before emitting a record."""
        with self.spinner.output_lock:
            self.spinner._clear_spinner_line()
            super().emit(record)
