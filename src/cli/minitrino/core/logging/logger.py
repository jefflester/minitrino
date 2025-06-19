"""MinitrinoLogger and logging configuration."""

import inspect
import logging
from contextlib import contextmanager
from types import FrameType
from typing import Callable, Optional

from click import prompt, style

from minitrino.core.logging.spinner import Spinner, SpinnerAwareHandler
from minitrino.core.logging.utils import LogLevel, MinitrinoLogFormatter, SinkHandler

DEFAULT_INDENT = " " * 5

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
    spinner(message: str) :
        Display a spinner and buffer the logs.
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
        self._spinner = Spinner(self, self.set_log_sink)

    def set_log_sink(self, sink: Callable[[str], None] | list[str] | None) -> None:
        """Set a log sink (callback or list)."""
        # Remove all SinkHandler instances to prevent duplicates
        for handler in list(self.logger.handlers):
            if isinstance(handler, SinkHandler):
                self.logger.removeHandler(handler)
        self._sink_handler = None
        self._log_sink = sink
        if sink is not None:
            handler = SinkHandler(sink)
            always_verbose = self._log_level == LogLevel.DEBUG
            handler.setFormatter(MinitrinoLogFormatter(always_verbose=always_verbose))
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

    @contextmanager
    def spinner(self, message: str):
        """Display a spinner while a task is in progress."""
        with self._spinner.spinner(message):
            yield

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


def configure_logging(
    log_level: LogLevel,
    logger: Optional[MinitrinoLogger] = None,
    global_logging: bool = False,
) -> None:
    """
    Configure logging for Minitrino and optionally globally.

    Parameters
    ----------
    log_level : LogLevel
        Minimum log level to emit.
    logger : MinitrinoLogger, optional
        The logger instance to use for spinner state. If None, a new
        instance is created.
    global_logging : bool, optional
        If True, configure root logger as well.
    """
    root_logger = logging.getLogger()
    minitrino_logger = logging.getLogger("minitrino")

    for logger_obj in (root_logger, minitrino_logger):
        for handler in list(logger_obj.handlers):
            logger_obj.removeHandler(handler)

    py_level = PY_LEVEL[log_level]
    always_verbose = log_level == LogLevel.DEBUG

    if logger is None:
        logger = MinitrinoLogger(log_level)

    handler = SpinnerAwareHandler(logger._spinner)
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
