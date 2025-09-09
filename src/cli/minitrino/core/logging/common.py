"""Common constants and utilities for Minitrino logging."""

import shutil

DEFAULT_INDENT = " " * 5


def get_terminal_width() -> int:
    """Get the terminal width."""
    return shutil.get_terminal_size(fallback=(80, 24)).columns
