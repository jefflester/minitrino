"""CommandResult dataclass for command execution results."""

from dataclasses import dataclass
from typing import Any


@dataclass
class CommandResult:
    """Command result.

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
    process_handle : Optional[Any]
        Optional handle to the underlying process (subprocess.Popen or exec_id).
        Used for streaming contexts to check process status.
    is_completed : bool
        Whether the command has completed execution.
        Used in streaming contexts to signal completion.
    """

    command: list[str]
    output: str
    exit_code: int
    duration: float
    error: BaseException | None = None
    process_handle: Any | None = None
    is_completed: bool = True
