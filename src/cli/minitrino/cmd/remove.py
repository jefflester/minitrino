"""Command to handle removal of containers, networks, and volumes."""

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import UserError


@click.command(
    "remove",
    help=(
        "Remove Minitrino resources. By default, applies to 'default' cluster.\n\n"
        "Remove resources for a specific cluster by using the CLUSTER_NAME "
        "environment variable or the --cluster / -c option, e.g.:\n\n"
        "minitrino -c my-cluster remove\n\n"
        "Or specify all clusters via:\n\n"
        "minitrino -c all remove"
    ),
)
@click.option(
    "-i",
    "--images",
    is_flag=True,
    default=False,
    help="Remove images. `--cluster` must be set to `all`.",
)
@click.option(
    "-v",
    "--volumes",
    is_flag=True,
    default=False,
    help="Remove volumes.",
)
@click.option(
    "-n",
    "--networks",
    is_flag=True,
    default=False,
    help="Remove networks.",
)
@click.option(
    "-m",
    "--module",
    "modules",
    type=str,
    default=[],
    multiple=True,
    help="Filter removal by module.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force removal.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext,
    images: bool,
    volumes: bool,
    networks: bool,
    modules: list[str],
    force: bool,
):
    """
    Handle removal of containers, networks, and volumes.

    Parameters
    ----------
    ctx : MinitrinoContext
        The Minitrino context.
    images : bool
        If True, removes Docker images tagged with Minitrino labels.
    volumes : bool
        If True, removes Docker volumes associated with Minitrino
        containers.
    networks : bool
        If True, removes Docker networks associated with the Minitrino
        cluster.
    modules : list[str]
        List of modules to filter removal by.
    force : bool
        If True, forces removal even if the resource is in use.
    """
    ctx.initialize()
    utils.check_daemon(ctx.docker_client)

    if images and modules:
        raise UserError(
            "Cannot remove images for a specific module because images are global "
            "resources.",
            "Run the command again without providing a module and ensure `--cluster "
            "all` is used to remove all images.",
        )

    remove_types = [
        t
        for t, enabled in (
            ("image", images),
            ("volume", volumes),
            ("network", networks),
        )
        if enabled
    ]
    if not remove_types:
        remove_types = ["image", "volume", "network"]

    modules = list(modules) or []
    for module in modules:
        ctx.modules.validate_module_name(module)

    remove_all = ctx.all_clusters and not modules and len(remove_types) == 3

    if remove_all:
        response = ctx.logger.prompt_msg(
            "You are about to remove all minitrino resources. Continue? [Y/N]"
        )
        if not utils.validate_yes(response):
            ctx.logger.info("Opted to skip resource removal.")
            return
        else:
            for t in remove_types:
                ctx.cluster.ops.remove(t, force, modules)
            return

    for t in remove_types:
        ctx.cluster.ops.remove(t, force, modules)

    ctx.logger.info("Removal complete.")
