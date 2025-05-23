"""Logging utilities for Minitrino clusters."""

from dataclasses import dataclass
from enum import Enum
from shutil import get_terminal_size
from textwrap import fill
from typing import Callable, Optional

from click import echo, prompt, style


@dataclass(frozen=True)
class LogMeta:
    """Logging metadata."""

    prefix: str
    color: str
    debug: bool = False


class LogLevel(Enum):
    """
    Log levels.

    Attributes
    ----------
    INFO : LogMeta
        Info level configuration (default).
    WARN : LogMeta
        Warning level configuration.
    ERROR : LogMeta
        Error level configuration.
    DEBUG : LogMeta
        Debug level configuration.
    """

    INFO = LogMeta("[i]  ", "cyan")
    WARN = LogMeta("[w]  ", "yellow")
    ERROR = LogMeta("[e]  ", "red")
    DEBUG = LogMeta("[v]  ", "magenta", True)


class MinitrinoLogger:
    """
    Minitrino logging utility.

    Parameters
    ----------
    log_level : LogLevel, optional
        Minimum log level to emit (default: INFO)

    Attributes
    ----------
    DEFAULT_INDENT : str
        Standard indent used for multi-line log output.

    Methods
    -------
    log(*args, level=LogLevel.INFO, stream=False) :
        Log a message with optional styling and indentation.
    info(*args, stream=False) :
        Log a message at the info level.
    warn(*args, stream=False) :
        Log a message at the warning level.
    error(*args, stream=False) :
        Log a message at the error level.
    debug(*args, stream=False) :
        Log a message at the debug level.
    prompt_msg(msg="") :
        Prompt the user with a message and capture input.
    set_log_sink(sink: Callable[[str], None] | list[str]) :
        Set a log sink (e.g., list or callback) for capturing log
        output. Useful for testing.
    styled_prefix(level=LogLevel.INFO) :
        Return the ANSI-styled log prefix.

    Notes
    -----
    This class provides standardized logging methods (`info`, `warn`,
    `error`, `debug`) that emit formatted messages to the console using
    `click.echo()`. It also supports interactive prompting and message
    styling with configurable verbosity.
    """

    DEFAULT_INDENT = " " * 5

    def __init__(self, log_level: Optional[LogLevel] = None) -> None:
        self._log_level = log_level if log_level is not None else LogLevel.INFO
        self._log_sink: Optional[Callable[[str], None] | list[str]] = None

    def should_log(self, level: LogLevel) -> bool:
        """Return True if the log should be emitted based on level."""
        order = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR]
        min_level_idx = order.index(self._log_level)
        msg_level_idx = order.index(level)
        return msg_level_idx >= min_level_idx

    def set_level(self, level: LogLevel) -> None:
        """Set the minimum log level."""
        self._log_level = level

    def log(
        self, *args: str, level: LogLevel = LogLevel.INFO, stream: bool = False
    ) -> None:
        """Log messages to the terminal using color-coded levels."""
        if not self.should_log(level):
            return

        for msg in args:
            lines = str(msg).replace("\r", "\n").split("\n")
            for i, line in enumerate(lines):
                formatted = self._format(line, level.value)
                if not formatted:
                    continue
                prefix = (
                    self.DEFAULT_INDENT
                    if stream or i > 0
                    else self.styled_prefix(level)
                )
                output = f"{prefix}{formatted}"
                # Write to sink if set
                if self._log_sink is not None:
                    if callable(self._log_sink):
                        self._log_sink(output)
                    elif isinstance(self._log_sink, list):
                        self._log_sink.append(output)
                echo(output)

    def info(self, *args: str, stream: bool = False) -> None:
        """Log an info-level message."""
        self.log(*args, level=LogLevel.INFO, stream=stream)

    def warn(self, *args: str, stream: bool = False) -> None:
        """Log a warning message."""
        self.log(*args, level=LogLevel.WARN, stream=stream)

    def error(self, *args: str, stream: bool = False) -> None:
        """Log an error message."""
        self.log(*args, level=LogLevel.ERROR, stream=stream)

    def debug(self, *args: str, stream: bool = False) -> None:
        """Log a debug message."""
        self.log(*args, level=LogLevel.DEBUG, stream=stream)

    def prompt_msg(self, msg: str = "") -> str:
        """Prompt the user with a styled message and return input."""
        msg = self._format(str(msg))
        styled_prefix = style(
            LogLevel.INFO.value.prefix, fg=LogLevel.INFO.value.color, bold=True
        )

        return prompt(
            f"{styled_prefix}{msg}",
            type=str,
        )

    def styled_prefix(self, level: LogLevel = LogLevel.INFO) -> str:
        """Return the ANSI-styled log prefix."""
        return style(level.value.prefix, fg=level.value.color, bold=True)

    def set_log_sink(self, sink: Callable[[str], None] | list[str]) -> None:
        """Set a log sink (callback or list)."""
        self._log_sink = sink

    def get_log_sink(self) -> Optional[Callable[[str], None] | list[str]]:
        """Get the current log sink, or None if unset."""
        return self._log_sink

    def _format(self, msg: str, meta: LogMeta = LogLevel.INFO.value) -> str:
        """
        Format a log message with the given metadata.

        Parameters
        ----------
        msg : str
            The message to format.
        meta : LogMeta
            The log metadata.

        Returns
        -------
        str
            Formatted log message string.
        """
        indent = self.DEFAULT_INDENT
        msg = fill(msg, width=get_terminal_size().columns - len(indent))
        return msg.replace("\n", "\n" + indent)
