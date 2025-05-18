"""Minitrino CLI entrypoint module."""

import os
import sys
import click
import difflib

from typing import Any
from importlib import import_module

from minitrino import utils
from minitrino.core.context import MinitrinoContext


class CommandLineInterface(click.MultiCommand):
    """Click MultiCommand class for loading and executing commands."""

    def list_commands(self, ctx) -> list[str]:
        """List available commands."""
        cmd_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "cmd"))
        commands = [
            filename[:-3].replace("_", "-")
            for filename in os.listdir(cmd_dir)
            if filename.endswith(".py") and not filename.startswith("__")
        ]
        return sorted(commands)

    def get_command(self, ctx, name) -> Any:
        """Load and return the command module."""
        from minitrino.core.logger import MinitrinoLogger

        logger = MinitrinoLogger()
        mod_name = name.replace("-", "_")
        try:
            mod = import_module(f"minitrino.cmd.{mod_name}")
        except ModuleNotFoundError:
            all_commands = self.list_commands(ctx)
            suggestion = difflib.get_close_matches(name, all_commands, n=1)
            suggestion_msg = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
            logger.error(f"Command '{name}' not found.{suggestion_msg}")
            sys.exit(1)
        cmd = getattr(mod, "cli", None)
        if cmd is None:
            logger.error(f"No 'cli' object in {mod_name}")
            sys.exit(1)
        return cmd


def version_string() -> str:
    """Return the version of the CLI and the library as a string."""
    cli_version = utils.cli_ver()
    try:
        ctx = MinitrinoContext()
        ctx.initialize(version_only=True)
        lib_version = utils.lib_ver(ctx=ctx)
    except Exception:
        lib_version = "NOT INSTALLED"
    return f"{cli_version} (library: {lib_version})"


@click.command(cls=CommandLineInterface)
@click.version_option(
    version=version_string(),  # type: ignore[arg-type]
    prog_name="minitrino",
    message="%(prog)s version %(version)s",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose logging output.",
)
@click.option(
    "-e",
    "--env",
    default=[],
    type=str,
    multiple=True,
    help="Add or override environment variables.",
)
@click.option(
    "-c",
    "--cluster",
    "cluster_name",
    default="",
    type=str,
    help="Sets the cluster name. Defaults to 'default'.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext, verbose: bool, env: list[str], cluster_name: str
) -> None:
    """Welcome to the Minitrino command line interface.

    To report issues or contribute, please visit:
    https://github.com/jefflester/minitrino
    """
    ctx.initialize(verbose, env, cluster_name)
