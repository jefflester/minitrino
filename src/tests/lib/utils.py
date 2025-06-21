"""Utility functions for Minitrino test library."""

import os
import shutil
import sys
from time import gmtime, strftime

import click

from tests import common

COLOR_OUTPUT = sys.stdout.isatty()
TERMINAL_WIDTH = shutil.get_terminal_size(fallback=(80, 24)).columns

SPECS = {
    "query": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "name": {"type": "string"},
            "sql": {"type": "string"},
            "trinoCliArgs": {"type": "array"},
            "contains": {"type": "array"},
            "rowCount": {"type": "number"},
            "env": {"type": "object"},
        },
        "required": ["type", "name", "sql"],
    },
    "shell": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "name": {"type": "string"},
            "command": {"type": "string"},
            "container": {"type": "string"},
            "contains": {"type": "array"},
            "exitCode": {"type": "number"},
            "env": {"type": "object"},
            "healthCheck": {
                "type": "object",
                "properties": {
                    "retries": {"type": "number"},
                    "command": {"type": "string"},
                    "container": {"type": "string"},
                    "contains": {"type": "array"},
                    "exitCode": {"type": "number"},
                },
                "required": ["command"],
            },
            "subCommands": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "retries": {"type": "number"},
                        "command": {"type": "string"},
                        "container": {"type": "string"},
                        "contains": {"type": "array"},
                        "exitCode": {"type": "number"},
                        "env": {"type": "object"},
                    },
                    "required": ["command"],
                },
            },
        },
        "required": ["type", "name", "command"],
    },
    "logs": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "name": {"type": "string"},
            "container": {"type": "string"},
            "contains": {"type": "array"},
            "timeout": {"type": "number"},
        },
        "required": ["type", "name", "container", "contains"],
    },
}


def dump_container_logs(debug=False) -> None:
    """Dump logs from containers."""
    if not debug:
        return
    containers = common.get_containers(all=True)
    for container in containers:
        log_msg = f"Dumping logs for container {container.name}:"
        sep = "=" * TERMINAL_WIDTH
        common.logger.info(f"{sep}\n{log_msg}\n{sep}")
        logs = container.logs().decode("utf-8")  # Decode binary logs to string
        common.logger.info(f"{logs}\n")


def record_failed_test(test_name: str, first: bool = False) -> None:
    """
    Record a failed test.

    Parameters
    ----------
    test_name : str
        The name of the failed test.
    first : bool
        Whether this is the first failed test. If True, the file is
        overwritten.
    """
    _file = os.path.join(common.MINITRINO_USER_DIR, ".lastfailed")
    try:
        with open(_file, "w+" if first else "a+") as f:
            f.write(f"{test_name}\n")
    except Exception as e:
        common.logger.error(f"Failed to record failed test: {e}")
        raise e


def get_failed_tests() -> list[str]:
    """Get the list of failed tests."""
    _file = os.path.join(common.MINITRINO_USER_DIR, ".lastfailed")
    try:
        with open(_file, "r+") as f:
            return f.read().splitlines()
    except Exception as e:
        common.logger.error(f"Failed to get failed tests: {e}")
        raise e


def _timestamp() -> str:
    """Return the current time as a formatted string for log prefix."""
    return strftime("%d/%m/%Y %H:%M:%S", gmtime())


def log_status(msg) -> None:
    """Log the status of a test."""
    click.echo(
        click.style(
            f"[{_timestamp()} GMT] [STATUS] ",
            fg="yellow",
            bold=True,
        )
        + msg,
        color=COLOR_OUTPUT,
    )
