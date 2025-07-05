"""CommandResult dataclass for command execution results."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandResult:
    """
    Command result.

    Attributes
    ----------
    command : list[str]
        The command that was executed.
    output : str
        The combined output of stdout and stderr.
    exit_code : int
        The exit code returned by the command.
    duration : float
        Duration in seconds for the command execution.
    error : Optional[BaseException]
        Error if command failed, else None.
    """

    command: list[str]
    output: str
    exit_code: int
    duration: float
    error: Optional[BaseException] = None
