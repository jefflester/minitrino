"""Error classes for Minitrino CLI."""


class MinitrinoError(Exception):
    """Base exception class for all Minitrino-related errors.

    Parameters
    ----------
    msg : str, optional
        Message to log and include in the exception.

    Attributes
    ----------
    msg : str
        Error message associated with the exception.
    exit_code : int
        Exit code for the error type. Defaults to 1.
    """

    exit_code = 1

    def __init__(self, msg: str = "") -> None:
        super().__init__(msg)
        self.msg = msg

    def __str__(self) -> str:
        """Return the error message as a string."""
        return self.msg


class UserError(MinitrinoError):
    """User errors that Minitrino can safely log and display.

    Attributes
    ----------
    msg : str
        Primary error message to display.
    hint_msg : str
        Optional user guidance for resolving the issue.
    exit_code : int
        Exit code used to signal a user-handled error. Defaults to 2.

    Parameters
    ----------
    msg : str, optional
        Message to log and include in the exception.
    hint_msg : str, optional
        Additional guidance for resolving the issue.
    """

    exit_code = 2

    def __init__(self, msg: str = "", hint_msg: str = "") -> None:
        if hint_msg:
            super().__init__(f"User error: {msg}\nHint: {hint_msg}")
        else:
            super().__init__(f"User error: {msg}")
