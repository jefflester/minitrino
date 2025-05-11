#!/usr/bin/env python3

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext


@click.command(
    "remove",
    help=(
        """Remove Minitrino resources. By default, applies to 'default' cluster.
        
        Remove resources for a specific cluster by using the `CLUSTER_NAME`
        environment variable or the `--cluster` / `-c` option, e.g.: 
        
        `minitrino -c my-cluster remove`, or specify all clusters via:\n
        `minitrino -c all remove`"""
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
    "-l",
    "--label",
    "labels",
    type=str,
    default=[],
    multiple=True,
    help="Filter removal by Docker labels (format: key-value pair(s)).",
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
    labels: list[str],
    force: bool,
):
    """
    Handles removal of containers, images, volumes, and networks associated with
    the Minitrino cluster environment. Supports full resource purges when used
    with `--cluster all`, and allows fine-grained control via resource type
    flags and label filters.

    Parameters
    ----------
    `images` : `bool`
        If True, removes Docker images tagged with Minitrino labels.
    `volumes` : `bool`
        If True, removes Docker volumes associated with Minitrino containers.
    `networks` : `bool`
        If True, removes Docker networks associated with the Minitrino cluster.
    `labels` : `list[str]`
        List of specific Docker label filters to target for removal.
    `force` : `bool`
        If True, forces removal even if the resource is in use.
    """
    utils.check_daemon(ctx.docker_client)

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

    labels = labels or []
    remove_all = ctx.all_clusters and not labels and len(remove_types) == 3

    if remove_all:
        response = ctx.logger.prompt_msg(
            "You are about to remove all minitrino resources. Continue? [Y/N]"
        )
        if not utils.validate_yes(response):
            ctx.logger.info("Opted to skip resource removal.")
            return
        else:
            for t in remove_types:
                ctx.cluster.ops.remove(t, force, labels)
            return

    for t in remove_types:
        ctx.cluster.ops.remove(t, force, labels)

    ctx.logger.info("Removal complete.")
