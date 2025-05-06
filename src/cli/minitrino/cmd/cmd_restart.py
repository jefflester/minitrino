#!/usr/bin/env python3

import sys
import click

from minitrino.components import Environment
from minitrino.cli import pass_environment
from minitrino import utils
from minitrino.settings import RESOURCE_LABEL


@click.command(
    "restart",
    help=("""Restart all running Minitrino cluster containers."""),
)
@utils.exception_handler
@pass_environment
def cli(ctx: Environment):
    """Restart command for Minitrino."""

    utils.check_daemon(ctx.docker_client)

    containers = ctx.docker_client.containers.list(
        filters={"label": RESOURCE_LABEL}, all=True
    )

    if len(containers) == 0:
        ctx.logger.info("No cluster containers to restart.")
        sys.exit(0)

    cluster_containers = [
        c.name
        for c in containers
        if c.name == "minitrino" or c.name.startswith("minitrino-worker")
    ]

    utils.restart_containers(ctx, cluster_containers, ctx.logger.INFO)
    ctx.logger.info("Restarted all cluster containers.")
