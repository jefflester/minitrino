"""Minitrino logger handler."""

import logging
import sys

from minitrino.core.logging.spinner import Spinner


class MinitrinoLoggerHandler(logging.StreamHandler):
    """Primary user-facing log handler for Minitrino.

    Clears the spinner line before emitting each log record to ensure clean CLI output
    during spinner operations.
    """

    def __init__(self, spinner: Spinner):
        super().__init__()
        self.spinner = spinner

    @property
    def stream(self):
        """Always return current sys.stderr instead of cached reference.

        This ensures the handler writes to whatever stderr currently points to,
        including CliRunner's capture buffer during tests.
        """
        return sys.stderr

    @stream.setter
    def stream(self, value):
        """Ignore attempts to set stream - always use current sys.stderr."""
        pass

    def emit(self, record: logging.LogRecord):
        """Emit a log record, always clearing spinner line first."""
        if record.levelno < self.level or not self.filter(record):
            return
        with self.spinner.output_lock:
            self.spinner._clear_spinner_line()
            super().emit(record)
