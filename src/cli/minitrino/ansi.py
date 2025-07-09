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
    ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_regex.sub("", value)
