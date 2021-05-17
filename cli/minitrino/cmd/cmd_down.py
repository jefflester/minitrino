#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import sys
import click

from minitrino.cli import pass_environment
from minitrino import utils
from minitrino import errors as err
from minitrino.settings import RESOURCE_LABEL


@click.command(
    "down",
    help=(
        """Bring down running Minitrino containers. This command follows the
        behavior of `docker-compose down` where containers are both stopped and
        removed."""
    ),
)
@click.option(
    "-k",
    "--keep",
    is_flag=True,
    default=False,
    help=(
        """Does not remove containers; instead, containers will only be
        stopped."""
    ),
)
@click.option(
    "--sig-kill",
    is_flag=True,
    default=False,
    help=("""Stop Minitrino containers without a grace period."""),
)
@utils.exception_handler
@pass_environment
def cli(ctx, sig_kill, keep):
    """Down command for Minitrino. Exits with a 0 status code if there are no
    running minitrino containers."""

    utils.check_daemon(ctx.docker_client)
    utils.check_lib(ctx)

    containers = ctx.docker_client.containers.list(
        filters={"label": RESOURCE_LABEL}, all=True
    )

    if len(containers) == 0:
        ctx.logger.log("No containers to bring down.")
        sys.exit(0)

    if sig_kill:
        stop_timeout = 1
        ctx.logger.log(
            "Stopping Minitrino containers with sig-kill...",
            level=ctx.logger.verbose,
        )
    else:
        stop_timeout = 10

    # Stop
    for container in containers:
        identifier = utils.generate_identifier(
            {"ID": container.short_id, "Name": container.name}
        )
        if container.status == "running":
            container.stop(timeout=stop_timeout)
            ctx.logger.log(f"Stopped container: {identifier}", level=ctx.logger.verbose)

    # Remove
    if not keep:
        for container in containers:
            identifier = utils.generate_identifier(
                {"ID": container.short_id, "Name": container.name}
            )
            container.remove()
            ctx.logger.log(f"Removed container: {identifier}", level=ctx.logger.verbose)

    ctx.logger.log("Brought down all Minitrino containers.")
