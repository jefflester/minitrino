"""Utility functions for Minitrino test library."""

import shutil
import sys
from time import gmtime, strftime

import click

from tests import common

COLOR_OUTPUT = sys.stdout.isatty()
TERMINAL_WIDTH = shutil.get_terminal_size(fallback=(80, 24)).columns


def cleanup(remove_images=False, debug=False) -> None:
    """
    Remove containers, networks, and volumes.

    Parameters
    ----------
    remove_images : bool
        Whether to remove images.
    debug : bool
        Whether to enable debug logging.
    """
    builder = common.CLICommandBuilder("all")
    cmd_down = builder.build_cmd("down", append=["--sig-kill"], verbose=debug)
    common.cli_cmd(cmd_down)
    cmd_remove = builder.build_cmd("remove", append=["--volumes"], verbose=debug)
    common.cli_cmd(cmd_remove)
    if remove_images:
        common.logger.info("Removing images...")
        common.execute_cmd(
            'docker images -q | grep -v "$(docker images minitrino/cluster -q)" | '
            "xargs -r docker rmi"
        )
    common.logger.info("Disk space usage:")
    common.execute_cmd("df -h")


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


def _timestamp() -> str:
    """Return the current time as a formatted string for log prefix."""
    return strftime("%d/%m/%Y %H:%M:%S", gmtime())


def log_success(msg, timestamp: str | None = None) -> None:
    """
    Log a success message.

    Parameters
    ----------
    msg : str
        The message to log.
    timestamp : str, optional
        Timestamp string to use as prefix (format: '%d/%m/%Y %H:%M:%S').
        If not provided, current time is used.
    """
    prefix = timestamp if timestamp is not None else _timestamp()
    click.echo(
        click.style(
            f"[{prefix} GMT] [SUCCESS] ",
            fg="green",
            bold=True,
        )
        + msg,
        color=COLOR_OUTPUT,
    )


def log_failure(msg, timestamp: str | None = None) -> None:
    """
    Log a failure message.

    Parameters
    ----------
    msg : str
        The message to log.
    timestamp : str, optional
        Timestamp string to use as prefix (format: '%d/%m/%Y %H:%M:%S').
        If not provided, current time is used.
    """
    prefix = timestamp if timestamp is not None else _timestamp()
    click.echo(
        click.style(
            f"[{prefix} GMT] [FAILURE] ",
            fg="red",
            bold=True,
        )
        + msg,
        color=COLOR_OUTPUT,
    )


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
