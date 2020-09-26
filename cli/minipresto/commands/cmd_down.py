#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import sys
import click

from minipresto.cli import LogLevel
from minipresto.cli import pass_environment
from minipresto.core import check_daemon
from minipresto.core import generate_identifier

from minipresto.settings import RESOURCE_LABEL


@click.command("down", help="""
Brings down all running Minipresto containers. This command follows the
behavior of `docker-compose down`, where containers are both stopped and
removed.
""")
@click.option("-k", "--keep", is_flag=True, default=False, help="""
Does not remove any containers; instead, they will only be stopped.
""")


@pass_environment
def cli(ctx, keep):
    """
    Down command for Minipresto. Exits with a 0 status code if there are no
    running minipresto containers.
    """

    check_daemon()

    containers = ctx.docker_client.containers.list(
        filters={"label": RESOURCE_LABEL}, all=True
    )

    if len(containers) == 0:
        ctx.log("No containers to bring down.")
        sys.exit(0)

    for container in containers:
        identifier = generate_identifier(
            {"ID": container.short_id, "Name": container.name}
        )
        container.stop()
        ctx.log(f"Stopped container: {identifier}", level=LogLevel().verbose)
    if not keep:
        for container in containers:
            identifier = generate_identifier(
                {"ID": container.short_id, "Name": container.name}
            )
            container.remove()  # Default behavior of Compose is to remove containers
            ctx.log(f"Removed container: {identifier}", level=LogLevel().verbose)

    ctx.log("Brought down all Minipresto containers.")
