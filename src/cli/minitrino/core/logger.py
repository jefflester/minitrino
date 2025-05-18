"""Logging utilities for Minitrino clusters."""

from click import echo, style, prompt
from textwrap import fill
from shutil import get_terminal_size
from enum import Enum
from dataclasses import dataclass


@dataclass(frozen=True)
class LogMeta:
    """Logging metadata."""

    prefix: str
    color: str
    verbose: bool = False


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
    VERBOSE : LogMeta
        Verbose level configuration.
    """

    INFO = LogMeta("[i]  ", "cyan")
    WARN = LogMeta("[w]  ", "yellow")
    ERROR = LogMeta("[e]  ", "red")
    VERBOSE = LogMeta("[v]  ", "magenta", True)


class MinitrinoLogger:
    """
    Minitrino logging utility.

    Parameters
    ----------
    log_verbose : bool, optional
        If `True`, verbose messages will be shown; otherwise, they are suppressed.

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
    verbose(*args, stream=False) :
        Log a message at the verbose level, if verbosity is enabled.
    prompt_msg(msg="") :
        Prompt the user with a message and capture input.
    styled_prefix(level=LogLevel.INFO) :
        Return the ANSI-styled log prefix.

    Notes
    -----
    This class provides standardized logging methods (`info`, `warn`, `error`,
    `verbose`) that emit formatted messages to the console using `click.echo()`. It also
    supports interactive prompting and message styling with configurable verbosity.
    """

    DEFAULT_INDENT = " " * 5

    def __init__(self, log_verbose: bool = False) -> None:
        self._log_verbose = log_verbose

    def log(
        self, *args: str, level: LogLevel = LogLevel.INFO, stream: bool = False
    ) -> None:
        """Log messages to the terminal using color-coded levels."""
        if level == LogLevel.VERBOSE and not self._log_verbose:
            return  # Suppress verbose messages if not enabled

        for msg in args:
            msgs = str(msg).replace("\r", "\n").split("\n")

            for i, msg in enumerate(msgs):
                msg = self._format(msg)
                if not msg:
                    continue
                msg_prefix = (
                    self.DEFAULT_INDENT
                    if stream or i > 0
                    else style(level.value.prefix, fg=level.value.color, bold=True)
                )
                echo(f"{msg_prefix}{msg}")

    def info(self, *args: str, stream: bool = False) -> None:
        """Log an info-level message."""
        self.log(*args, level=LogLevel.INFO, stream=stream)

    def warn(self, *args: str, stream: bool = False) -> None:
        """Log a warning message."""
        self.log(*args, level=LogLevel.WARN, stream=stream)

    def error(self, *args: str, stream: bool = False) -> None:
        """Log an error message."""
        self.log(*args, level=LogLevel.ERROR, stream=stream)

    def verbose(self, *args: str, stream: bool = False) -> None:
        """Log a verbose message if verbosity is enabled."""
        if self._log_verbose:
            self.log(*args, level=LogLevel.VERBOSE, stream=stream)

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

    def _format(self, msg: str, meta: LogMeta) -> str:
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
        msg = msg.replace("\n", "\n" + indent)
        return style(f"{meta.prefix}{msg}", fg=meta.color)
