"""Commands for installing Minitrino libraries."""

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext


@click.command(
    "lib-install",
    help="Install the Minitrino library.",
)
@click.option(
    "-v",
    "--version",
    default="",
    type=str,
    help="Library version.",
)
@click.option(
    "-r",
    "--list-releases",
    is_flag=True,
    default=False,
    help="List all available Minitrino library releases.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(ctx: MinitrinoContext, version: str, list_releases: bool) -> None:
    """
    Install the Minitrino library from a tagged GitHub release.

    If a library directory already exists, prompt the user for
    permission before overwriting it. The version defaults to the
    current CLI version if not explicitly specified.

    Parameters
    ----------
    version : str
        The library version to install. If empty, defaults to the CLI
        version.
    list_releases : bool
        If True, list all available releases and exit.
    """
    ctx.initialize()
    ctx.lib_manager()

    if list_releases:
        releases = ctx.lib_manager.list_releases()
        ctx.logger.info("Available Minitrino releases:")
        ctx.logger.info(*sorted(releases))
        return