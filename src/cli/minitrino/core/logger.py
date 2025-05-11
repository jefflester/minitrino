#!/usr/bin/env python3

from click import echo, style, prompt
from textwrap import fill
from shutil import get_terminal_size
from enum import Enum
from dataclasses import dataclass


@dataclass(frozen=True)
class LogMeta:
    prefix: str
    color: str
    verbose: bool = False


class LogLevel(Enum):
    """
    Logging level configuration.

    Attributes
    ----------
    `INFO` : `LogMeta`
        Info level configuration (default).
    `WARN` : `LogMeta`
        Warning level configuration.
    `ERROR` : `LogMeta`
        Error level configuration.
    `VERBOSE` : `LogMeta`
        Verbose level configuration.
    """

    INFO = LogMeta("[i]  ", "cyan")
    WARN = LogMeta("[w]  ", "yellow")
    ERROR = LogMeta("[e]  ", "red")
    VERBOSE = LogMeta("[v]  ", "magenta", True)


class MinitrinoLogger:
    """
    Minitrino logging utility for color-coded terminal output.

    This class provides standardized logging methods (`info`, `warn`, `error`,
    `verbose`) that emit formatted messages to the console using `click.echo()`.
    It also supports interactive prompting and message styling with configurable
    verbosity.

    Constructor Parameters
    ----------------------
    `log_verbose` : `bool`, optional
        If `True`, verbose messages will be shown; otherwise, they are
        suppressed.

    Attributes
    ----------
    `DEFAULT_INDENT` : `str`
        Standard indent used for multi-line log output.

    Methods
    -------
    `log(*args, level=LogLevel.INFO, stream=False)` :
        Logs a message with optional styling and indentation.
    `info(*args, stream=False)` :
        Logs a message at the info level.
    `warn(*args, stream=False)` :
        Logs a message at the warning level.
    `error(*args, stream=False)` :
        Logs a message at the error level.
    `verbose(*args, stream=False)` :
        Logs a message at the verbose level, if verbosity is enabled.
    `prompt_msg(msg="")` :
        Prompts the user with a message and captures input.
    `styled_prefix(level=LogLevel.INFO)` :
        Returns the ANSI-styled log prefix.
    """

    DEFAULT_INDENT = " " * 5

    def __init__(self, log_verbose: bool = False) -> None:
        self._log_verbose = log_verbose

    def log(
        self, *args: str, level: LogLevel = LogLevel.INFO, stream: bool = False
    ) -> None:
        """
        Logs messages to the terminal using color-coded levels.

        Parameters
        ----------
        `*args` : `str`
            Messages to log.
        `level` : `LogLevel`, optional
            Logging level configuration. Defaults to LogLevel.INFO.
        `stream` : `bool`, optional
            If True, disables prefix on multi-line streamed output.
        """

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
        """Logs an info-level message."""
        self.log(*args, level=LogLevel.INFO, stream=stream)

    def warn(self, *args: str, stream: bool = False) -> None:
        """Logs a warning message."""
        self.log(*args, level=LogLevel.WARN, stream=stream)

    def error(self, *args: str, stream: bool = False) -> None:
        """Logs an error message."""
        self.log(*args, level=LogLevel.ERROR, stream=stream)

    def verbose(self, *args: str, stream: bool = False) -> None:
        """Logs a verbose message."""
        if self._log_verbose:
            self.log(*args, level=LogLevel.VERBOSE, stream=stream)

    def prompt_msg(self, msg: str = "") -> str:
        """
        Prompts the user with a styled message and returns input.

        Parameters
        ----------
        `msg` : `str`, optional
            Message to display before input prompt.

        Returns
        -------
        `str`
            User-entered string.
        """

        msg = self._format(str(msg))
        styled_prefix = style(
            LogLevel.INFO.value.prefix, fg=LogLevel.INFO.value.color, bold=True
        )

        return prompt(
            f"{styled_prefix}{msg}",
            type=str,
        )

    def styled_prefix(self, level: LogLevel = LogLevel.INFO) -> str:
        """
        Returns a styled log-level prefix.

        Parameters
        ----------
        `level` : `LogLevel`, optional
            Logging level configuration. Defaults to LogLevel.INFO.

        Returns
        -------
        `str`
            ANSI-styled prefix string.
        """
        return style(level.value.prefix, fg=level.value.color, bold=True)

    def _format(self, msg: str) -> str:
        """
        Formats a message for clean terminal output.

        Parameters
        ----------
        `msg` : `str`
            The message to format.

        Returns
        -------
        `str`
            Formatted string for terminal display.
        """

        msg = msg.rstrip()
        if not msg:
            return ""

        terminal_width, _ = get_terminal_size()
        msg = msg.replace("\n", f"\n{self.DEFAULT_INDENT}")
        msg = fill(
            msg,
            terminal_width - 4,
            subsequent_indent=self.DEFAULT_INDENT,
            replace_whitespace=False,
            break_on_hyphens=False,
            break_long_words=True,
        )

        return msg
