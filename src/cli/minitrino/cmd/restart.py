"""Command to restart containers in the environment."""

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext


@click.command(
    "restart",
    help=(
        """Restart running containers. By default, applies to 'default' cluster.
        
        Restart containers in a specific cluster by using the `CLUSTER_NAME` environment
        variable or the `--cluster` / `-c` option, e.g.: `minitrino -c all restart`"""
    ),
)
@utils.exception_handler
@utils.pass_environment()
def cli(ctx: MinitrinoContext):
    """Restart cluster containers.

    Restarts all containers in the cluster, including coordinator and workers.
    """
    utils.check_daemon(ctx.docker_client)
    ctx.cluster.ops.restart()
