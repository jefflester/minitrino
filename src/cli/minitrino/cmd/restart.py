#!/usr/bin/env python3

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext


@click.command(
    "restart",
    help=(
        """Restart running containers. By default, applies to 'default' cluster.
        
        Restart containers in a specific cluster by using the `CLUSTER_NAME`
        environment variable or the `--cluster` / `-c` option, e.g.: 
        
        `minitrino -c my-cluster restart`, or restart all clusters via:\n
        `minitrino -c all restart`"""
    ),
)
@utils.exception_handler
@utils.pass_environment()
def cli(ctx: MinitrinoContext) -> None:
    """Restart running container in the target cluster.

    By default, it applies to the 'default' cluster, but an alternative cluster
    can be specified using the `--cluster` option or the `CLUSTER_NAME`
    environment variable."""

    utils.check_daemon(ctx.docker_client)
    ctx.cluster.ops.restart()
