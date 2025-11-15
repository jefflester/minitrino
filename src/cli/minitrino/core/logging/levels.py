"""Log levels for the Minitrino logger."""

import logging
from enum import Enum


class LogLevel(Enum):
    """Logging levels for Minitrino.

    Attributes
    ----------
    prefix : str
        The prefix for the log level.
    color : str
        The color for the log level.
    debug : bool
        Whether the log level is debug.
    """

    INFO = ("[i]  ", "cyan", False)
    WARN = ("[w]  ", "yellow", False)
    ERROR = ("[e]  ", "red", False)
    DEBUG = ("[v]  ", "magenta", True)

    def __init__(self, prefix: str, color: str, debug: bool):
        self.prefix = prefix
        self.color = color
        self.debug = debug


PY_LEVEL = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARN: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
}
