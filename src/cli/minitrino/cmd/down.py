#!/usr/bin/env python3

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext


@click.command(
    "down",
    help=(
        """Stop and remove all running cluster containers. By default, applies
        to cluster 'default'.
        
        Stop and remove containers in specific cluster by using the
        `CLUSTER_NAME` environment variable or the `--cluster` / `-c` option,
        e.g.: 
        
        `minitrino -c my-cluster down`, or stop all clusters via:\n`minitrino -c
        all down`"""
    ),
)
@click.option(
    "-k",
    "--keep",
    is_flag=True,
    default=False,
    help="Do not remove containers; only stop them.",
)
@click.option(
    "--sig-kill",
    is_flag=True,
    default=False,
    help="Stop containers without a grace period.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(ctx: MinitrinoContext, sig_kill: bool, keep: bool) -> None:
    """
    Stops and optionally removes all running containers for the active or
    specified cluster(s).

    Containers are stopped and removed unless the `--keep` flag is passed.

    Parameters
    ----------
    `sig_kill` : `bool`
        If True, stops containers immediately without a grace period.
    `keep` : `bool`
        If True, stops containers but does not remove them.
    """

    utils.check_daemon(ctx.docker_client)
    utils.check_lib(ctx)

    ctx.cluster.ops.down(sig_kill=sig_kill, keep=keep)
