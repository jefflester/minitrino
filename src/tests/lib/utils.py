"""Utility functions for Minitrino test library."""

import sys
from time import gmtime, strftime

import click

from tests import common

COLOR_OUTPUT = sys.stdout.isatty()


def cleanup(remove_images=False, debug=False, x=False) -> None:
    """
    Remove containers, networks, and volumes.

    Parameters
    ----------
    remove_images : bool
        Whether to remove images.
    debug : bool
        Whether to enable debug logging.
    x : bool
        Whether to exit on failure; do not rollback resources.
    """
    if not x:
        debug_args = "-v --global-logging" if debug else ""
        common.execute_cmd(f"minitrino -c all {debug_args} down --sig-kill")
        common.execute_cmd(f"minitrino -c all {debug_args} remove --volumes")
        if remove_images:
            print("Removing images...")
            common.execute_cmd(
                'docker images -q | grep -v "$(docker images minitrino/cluster -q)" | '
                "xargs -r docker rmi"
            )
    print("Disk space usage:")
    common.execute_cmd("df -h")


def dump_container_logs(debug=False) -> None:
    """Dump logs from containers."""
    if not debug:
        return
    containers = common.get_containers(all=True)
    for container in containers:
        log_msg = f"Dumping logs for container {container.name}:"
        sep = "=" * len(log_msg)
        print(f"{sep}\n{log_msg}\n{sep}")
        logs = container.logs().decode("utf-8")  # Decode binary logs to string
        print(f"{logs}\n")


def log_success(msg) -> None:
    """Log a success message."""
    click.echo(
        click.style(
            f"[{strftime('%d/%m/%Y %H:%M:%S', gmtime())} GMT] [SUCCESS] ",
            fg="green",
            bold=True,
        )
        + msg,
        color=COLOR_OUTPUT,
    )


def log_status(msg) -> None:
    """Log the status of a test."""
    click.echo(
        click.style(
            f"[{strftime('%d/%m/%Y %H:%M:%S', gmtime())} GMT] [RUNNING] ",
            fg="yellow",
            bold=True,
        )
        + msg,
        color=COLOR_OUTPUT,
    )
