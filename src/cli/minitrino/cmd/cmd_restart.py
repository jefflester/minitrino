#!/usr/bin/env python3

import sys
import click

from minitrino.components import Environment
from minitrino.cli import pass_environment
from minitrino import utils
from minitrino.settings import COMPOSE_LABEL
from minitrino.settings import RESOURCE_LABEL


@click.command(
    "restart",
    help=(
        """Restart all running cluster containers. By default, applies to
        'default' cluster.
        
        Restart containers in specific cluster by using the `CLUSTER_NAME`
        environment variable or the `--cluster-name` / `-c` option, e.g.: 
        
        `minitrino -c my-cluster restart`, or restart all clusters via:\n
        `minitrino -c '*' restart`"""
    ),
)
@utils.exception_handler
@pass_environment
def cli(ctx: Environment):
    """Restart command for Minitrino."""

    utils.check_daemon(ctx.docker_client)

    cluster_resources = ctx.get_cluster_resources()
    containers = cluster_resources["containers"]

    if len(containers) == 0:
        ctx.logger.info("No cluster containers to restart.")
        sys.exit(0)

    cluster_containers = [
        c.name
        for c in containers
        if c.name == f"minitrino-{ctx.cluster_name}"
        or c.name.startswith("minitrino-worker")
    ]

    utils.restart_containers(ctx, cluster_containers, ctx.logger.INFO)
    ctx.logger.info("Restarted all cluster containers.")
