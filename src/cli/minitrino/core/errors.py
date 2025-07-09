"""Error classes for Minitrino CLI."""

import traceback


class MinitrinoError(Exception):
    """
    Base exception class for all Minitrino-related errors.

    Parameters
    ----------
    msg : str, optional
        Message to log and include in the exception.
    caught_error : BaseException | None, optional
        The exception that was caught and re-raised.

    Attributes
    ----------
    msg : str
        Error message associated with the exception.
    caught_error : BaseException | None
        The exception that was caught and re-raised.
    exit_code : int
        Exit code for the error type. Defaults to 1.
    """

    exit_code = 1

    def __init__(
        self, msg: str = "", caught_error: BaseException | None = None
    ) -> None:
        super().__init__(msg)
        self.msg = msg
        self.caught_error = caught_error

    def __str__(self) -> str:
        """Return the error message as a string."""
        if self.caught_error:
            tb = traceback.format_exception(
                type(self.caught_error),
                self.caught_error,
                self.caught_error.__traceback__,
            )
            return f"{self.msg}\nCaught error: {tb}"
        return self.msg


class UserError(MinitrinoError):
    """
    User errors that Minitrino can safely log and display.

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
