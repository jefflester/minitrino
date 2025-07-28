"""Logging formatter for Minitrino logger."""

import logging
import os
import sys
import textwrap

from click import style

from minitrino.core.logging.common import DEFAULT_INDENT, get_terminal_width
from minitrino.core.logging.levels import LogLevel


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
        "DEBUG": "[v]  ",
        "INFO": "[i]  ",
        "WARNING": "[w]  ",
        "ERROR": "[e]  ",
        "CRITICAL": "[e]  ",
    }

    def __init__(self, always_verbose=False):
        """Initialize the formatter."""
        super().__init__()
        self.always_verbose = always_verbose
        self.enable_color = sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record for output.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to format.

        Returns
        -------
        str
            The formatted log message.
        """
        msg = record.getMessage()
        if not msg.strip():
            return ""

        prefix = self._get_prefix(record)
        left = self._get_left_prefix(record, prefix)
        lines = msg.splitlines()
        if not lines:
            return left
        if sys.stdout.isatty():
            return self._wrap_lines_tty(lines, left)
        else:
            return self._wrap_lines_plain(lines, left)

    def _get_prefix(self, record: logging.LogRecord) -> str:
        """
        Get the prefix for the log record, applying color if enabled.

        Parameters
        ----------
        record : logging.LogRecord
            The log record.

        Returns
        -------
        str
            The prefix.
        """
        prefix = self.PREFIXES.get(record.levelname, LogLevel.INFO.prefix)
        color = self.COLORS.get(record.levelname, LogLevel.INFO.color)
        if self.enable_color:
            return style(prefix, fg=color, bold=True)
        return prefix

    def _get_left_prefix(self, record: logging.LogRecord, prefix: str) -> str:
        """
        Get the left-side prefix for the log message.

        Parameters
        ----------
        record : logging.LogRecord
            The log record.
        prefix : str
            The prefix string (styled or plain).

        Returns
        -------
        str
            The left prefix for the message.
        """
        fq_caller = getattr(record, "fq_caller", "")
        if self.always_verbose or record.levelno == logging.DEBUG:
            if fq_caller:
                return f"{prefix}{fq_caller} "
            elif record.pathname:
                return f"{prefix}{os.path.basename(record.pathname)}:{record.lineno} "
        return prefix

    def _wrap_lines_tty(self, lines: list[str], left: str) -> str:
        """
        Wrap lines for TTY output using textwrap, with indentation.

        Parameters
        ----------
        lines : list of str
            The message lines to wrap.
        left : str
            The left prefix for the first line.

        Returns
        -------
        str
            The wrapped message.
        """
        # First line gets the prefix, subsequent lines get default indent
        first_wrapper = textwrap.TextWrapper(
            width=get_terminal_width(),
            initial_indent=left,
            subsequent_indent=DEFAULT_INDENT,
        )
        # Subsequent original lines get default indent
        other_wrapper = textwrap.TextWrapper(
            width=get_terminal_width(),
            initial_indent=DEFAULT_INDENT,
            subsequent_indent=DEFAULT_INDENT,
        )

        wrapped_lines = []
        for i, line in enumerate(lines):
            if i == 0:
                wrapped_lines.append(first_wrapper.fill(line))
            else:
                wrapped_lines.append(other_wrapper.fill(line))
        return "\n".join(wrapped_lines)

    def _wrap_lines_plain(self, lines: list[str], left: str) -> str:
        """
        Format lines for non-TTY output.

        Parameters
        ----------
        lines : list of str
            The message lines to wrap.
        left : str
            The left prefix for the first line.

        Returns
        -------
        str
            The formatted message.
        """
        return "\n".join(
            [f"{left}{lines[0]}"] + [f"{DEFAULT_INDENT}{line}" for line in lines[1:]]
        )
