"""Strip ANSI escape sequences from strings."""

import re


def strip_ansi(value: str = "") -> str:
    """
    Remove ANSI escape sequences from the given string.

    Parameters
    ----------
    value : str, optional
        Input string possibly containing ANSI escape codes.

    Returns
    -------
    str
        The cleaned string with ANSI codes removed.
    """
    # Handle OSC sequences first (terminal title, hyperlinks, etc.)
    # OSC sequences can be terminated with \x07 (BEL) or \x1b\\ (ST)
    value = re.sub(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", "", value)
    # Handle CSI sequences and other escape codes
    value = re.sub(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", value)
    return value
