"""Logging utilities for Minitrino."""

import logging
import os
import sys
from enum import Enum
from typing import Callable

from click import style

DEFAULT_INDENT = " " * 5


class LogLevel(Enum):
    """Logging levels for Minitrino."""

    INFO = ("[i]  ", "cyan", False)
    WARN = ("[w]  ", "yellow", False)
    ERROR = ("[e]  ", "red", False)
    DEBUG = ("[v]  ", "magenta", True)

    def __init__(self, prefix: str, color: str, debug: bool):
        self.prefix = prefix
        self.color = color
        self.debug = debug


class SinkHandler(logging.Handler):
    """Logging handler that sends log records to a sink."""

    def __init__(
        self, sink: Callable[[str, str, bool], None] | list[tuple[str, bool, str]]
    ):
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the sink.

        Tags the log record with the stream and spinner artifact status.
        """
        msg = self.format(record)
        stream = "stderr" if record.levelno >= logging.ERROR else "stdout"
        is_spinner_artifact = getattr(record, "is_spinner_artifact", False)
        if callable(self.sink):
            self.sink(msg, stream, is_spinner_artifact)
        elif isinstance(self.sink, list):
            self.sink.append((msg, is_spinner_artifact, stream))


class MinitrinoLogFormatter(logging.Formatter):
    """Formatter for Minitrino logs."""

    COLORS = {
        "DEBUG": "magenta",
        "INFO": "cyan",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red",
    }
    PREFIXES = {
        "DEBUG": "[v]",
        "INFO": "[i]",
        "WARNING": "[w]",
        "ERROR": "[e]",
        "CRITICAL": "[e]",
    }

    def __init__(self, always_verbose=False):
        super().__init__()
        self.always_verbose = always_verbose
        self.enable_color = sys.stdout.isatty()

    def format(self, record: logging.LogRecord):
        """Format a log record."""
        logger_name = record.name
        prefix = self.PREFIXES.get(record.levelname, "[i]")
        color = self.COLORS.get(record.levelname, "cyan")
        if self.enable_color:
            styled_prefix = style(prefix, fg=color, bold=True)
        else:
            styled_prefix = prefix

        msg = record.getMessage()

        if self.always_verbose or record.levelno != logging.INFO:
            if record.pathname:
                filename = os.path.basename(record.pathname)
            else:
                filename = record.module
            lineno = record.lineno
            left = f"{styled_prefix} {logger_name}:{filename}:{lineno} "
            lines = msg.splitlines()
            if not lines:
                return left
            formatted = [f"{left}{lines[0]}"]
            for line in lines[1:]:
                formatted.append(f"{DEFAULT_INDENT}{line}")
            return "\n".join(formatted)
        else:
            return f"{styled_prefix} {msg}"
