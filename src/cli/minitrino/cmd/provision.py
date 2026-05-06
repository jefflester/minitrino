"""Provisioning commands for Minitrino CLI."""

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext


@click.command(
    "provision",
    help="Provision a cluster with optional modules.",
)
@click.option(
    "-m",
    "--module",
    "modules",
    default=[],
    type=str,
    multiple=True,
    help="Module to install in the cluster.",
)
@click.option(
    "-i",
    "--image",
    default="",
    type=str,
    help="Cluster image type (trino or starburst). Defaults to trino.",
)
@click.option(
    "-w",
    "--workers",
    "workers",
    default=0,
    type=int,
    help="Number of cluster workers to provision (default: 0).",
)
@click.option(
    "-n",
    "--no-rollback",
    is_flag=True,
    default=False,
    help="Disables cluster rollback if provisioning fails.",
)
@click.option(
    "-s",
    "--source-code",
    "source_code",
    default=None,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help=(
        "Path to a local Trino or Starburst source repo (or direct "
        "distribution directory). Builds the image from local Maven "
        "output instead of downloading a published tarball."
    ),
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext,
    modules: tuple[str, ...],
    image: str,
    workers: int,
    no_rollback: bool,
    source_code: str | None,
) -> None:
    """Provision the cluster and environment dependencies.

    Parameters
    ----------
    modules : list[str]
        One or more modules to provision in the cluster.
    image : str
        Cluster image type (trino or starburst).
    workers : int
        Number of cluster workers to provision.
    no_rollback : bool
        If True, disables rollback on failure.
    source_code : str or None
        Path to a local source repository or distribution directory.

    Notes
    -----
    If no options are provided, a standalone coordinator is provisioned.
    Supports Trino or Starburst distributions, and dynamic worker
    scaling. Dependent clusters are automatically provisioned after the
    primary cluster is launched.
    """
    ctx.initialize()
    modules_list = list(modules)
    ctx.cluster.ops.provision(modules_list, image, workers, no_rollback, source_code)
