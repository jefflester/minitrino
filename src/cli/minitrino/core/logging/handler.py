"""Minitrino logger handler."""

import logging

from minitrino.core.logging.spinner import Spinner


class MinitrinoLoggerHandler(logging.StreamHandler):
    """
    Primary user-facing log handler for Minitrino.

    Clears the spinner line before emitting each log record to ensure
    clean CLI output during spinner operations.
    """

    def __init__(self, spinner: Spinner):
        super().__init__()
        self.spinner = spinner

    def emit(self, record: logging.LogRecord):
        """Emit a log record, always clearing spinner line first."""
        if record.levelno < self.level or not self.filter(record):
            return
        with self.spinner.output_lock:
            self.spinner._clear_spinner_line()
            super().emit(record)
