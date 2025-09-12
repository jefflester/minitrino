"""Command to restart containers in the environment."""

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext


@click.command(
    "restart",
    help=(
        "Restart running cluster containers (coordinator and workers). By "
        "default, applies to 'default' cluster.\n\n"
        "Restart containers in a specific cluster by using the CLUSTER_NAME "
        "environment variable or the --cluster / -c option, e.g.:\n\n"
        "minitrino -c my-cluster restart"
    ),
)
@utils.exception_handler
@utils.pass_environment()
def cli(ctx: MinitrinoContext):
    """Restart cluster containers."""
    ctx.initialize()
    utils.check_daemon(ctx.docker_client)
    with ctx.logger.spinner("Restarting containers..."):
        ctx.cluster.ops.restart()
