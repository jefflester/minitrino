"""Utility functions for Minitrino test library."""

from time import gmtime, strftime

import click

from test import common


def cleanup(remove_images=False) -> None:
    """
    Remove containers, networks, and volumes.

    Parameters
    ----------
    remove_images : bool
        Whether to remove images.
    """
    common.execute_cmd("minitrino -v down --sig-kill")
    common.execute_cmd("minitrino -v remove --volumes")

    if remove_images:
        print("Removing images...")
        common.execute_cmd(
            'docker images -q | grep -v "$(docker images minitrino/cluster -q)" | '
            "xargs -r docker rmi"
        )

    print("Disk space usage:")
    common.execute_cmd("df -h")


def dump_container_logs() -> None:
    """Dump logs from containers."""
    containers = common.get_containers(all=True)
    for container in containers:
        print(f"Dumping logs for container {container.name}:")
        logs = container.logs().decode("utf-8")  # Decode binary logs to string
        print(logs)
        print("\n")


def log_success(msg) -> None:
    """Log a success message."""
    click.echo(
        click.style(
            f"[{strftime('%d/%m/%Y %H:%M:%S', gmtime())} GMT] [SUCCESS] ",
            fg="green",
            bold=True,
        )
        + msg
        + "\n"
    )


def log_status(msg) -> None:
    """Log the status of a test."""
    click.echo(
        click.style(
            f"[{strftime('%d/%m/%Y %H:%M:%S', gmtime())} GMT] [RUNNING] ",
            fg="yellow",
            bold=True,
        )
        + msg
        + "\n"
    )
