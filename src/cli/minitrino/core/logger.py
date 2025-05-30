"""Logging utilities for Minitrino clusters."""

import inspect
import logging
import os
import sys
from enum import Enum
from types import FrameType
from typing import Callable, Optional

from click import prompt, style

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

    def __init__(self, sink: Callable[[str], None] | list[str]):
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the sink."""
        msg = self.format(record)
        if callable(self.sink):
            self.sink(msg)
        elif isinstance(self.sink, list):
            self.sink.append(msg)


PY_LEVEL = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARN: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
}


class MinitrinoLogger:
    """
    Minitrino logging utility.

    Parameters
    ----------
    log_level : LogLevel, optional
        Minimum log level to emit (default: INFO)

    Methods
    -------
    log(*args, level=LogLevel.INFO) :
        Log a message with optional styling and indentation.
    info(*args) :
        Log a message at the info level.
    warn(*args) :
        Log a message at the warning level.
    error(*args) :
        Log a message at the error level.
    debug(*args) :
        Log a message at the debug level.
    prompt_msg(msg="") :
        Prompt the user with a message and capture input.
    set_log_sink(sink: Callable[[str], None] | list[str]) :
        Set a log sink (e.g., list or callback) for capturing log
        output. Useful for testing.
    styled_prefix(level=LogLevel.INFO) :
        Return the ANSI-styled log prefix.
    """

    def __init__(self, log_level: Optional[LogLevel] = None) -> None:
        self._log_level = log_level if log_level is not None else LogLevel.INFO
        self.logger = logging.getLogger("minitrino")
        self.set_level(self._log_level)
        self._log_sink: Optional[Callable[[str], None] | list[str]] = None
        self._sink_handler: Optional[SinkHandler] = None

    def set_log_sink(self, sink: Callable[[str], None] | list[str]) -> None:
        """Set a log sink (callback or list)."""
        if self._sink_handler is not None:
            self.logger.removeHandler(self._sink_handler)
            self._sink_handler = None
        self._log_sink = sink
        if sink is not None:
            handler = SinkHandler(sink)
            for h in self.logger.handlers:
                if isinstance(h, logging.StreamHandler):
                    handler.setFormatter(h.formatter)
                    break
            self.logger.addHandler(handler)
            self._sink_handler = handler

    def get_log_sink(self) -> Optional[Callable[[str], None] | list[str]]:
        """Return the current log sink."""
        return self._log_sink

    def set_level(self, level: LogLevel) -> None:
        """Set the log level."""
        self._log_level = level
        py_level = PY_LEVEL[level]
        self.logger.setLevel(py_level)

    def log(self, *args: str, level: LogLevel = LogLevel.INFO) -> None:
        """Log a message."""
        py_level = PY_LEVEL[level]
        msg = " ".join(str(a) for a in args)
        logger = self._get_caller_logger()
        logger.log(py_level, msg, stacklevel=3)

    def info(self, *args: str) -> None:
        """Log an info message."""
        self.log(*args, level=LogLevel.INFO)

    def warn(self, *args: str) -> None:
        """Log a warning message."""
        self.log(*args, level=LogLevel.WARN)

    def error(self, *args: str) -> None:
        """Log an error message."""
        self.log(*args, level=LogLevel.ERROR)

    def debug(self, *args: str) -> None:
        """Log a debug message."""
        self.log(*args, level=LogLevel.DEBUG)

    def prompt_msg(self, msg: str = "") -> str:
        """Prompt the user with a message and capture input."""
        msg = str(msg)
        styled_prefix = style(LogLevel.INFO.prefix, fg=LogLevel.INFO.color, bold=True)
        return prompt(f"{styled_prefix}{msg}", type=str)

    def styled_prefix(self, level: LogLevel = LogLevel.INFO) -> str:
        """Return the ANSI-styled log prefix."""
        return style(level.prefix, fg=level.color, bold=True)

    def _get_caller_logger(self) -> logging.Logger:
        frame: Optional[FrameType] = inspect.currentframe()
        if frame is None:
            return logging.getLogger("minitrino")
        for _ in range(3):
            if frame.f_back is None:
                break
            frame = frame.f_back
        module = inspect.getmodule(frame)
        logger_name = module.__name__ if module else "minitrino"
        return logging.getLogger(logger_name)


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


def configure_logging(log_level: LogLevel, global_logging: bool = False) -> None:
    """Configure logging for Minitrino and optionally globally."""
    root_logger = logging.getLogger()
    minitrino_logger = logging.getLogger("minitrino")

    for logger in (root_logger, minitrino_logger):
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

    py_level = PY_LEVEL[log_level]
    always_verbose = log_level == LogLevel.DEBUG
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(MinitrinoLogFormatter(always_verbose=always_verbose))

    if global_logging:
        root_logger.addHandler(handler)
        root_logger.setLevel(py_level)
        minitrino_logger.propagate = True
    else:
        minitrino_logger.addHandler(handler)
        minitrino_logger.setLevel(py_level)
        minitrino_logger.propagate = False
        root_logger.setLevel(logging.WARNING)
        for name in logging.root.manager.loggerDict:
            if not name.startswith("minitrino"):
                logging.getLogger(name).setLevel(logging.WARNING)
