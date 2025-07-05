"""Minitrino CLI entrypoint."""

import logging
import os
import sys
from importlib import import_module
from typing import Any

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import UserError
from minitrino.core.logging.logger import LogLevel, MinitrinoLogger, configure_logging

# Singleton logger instantiated at entrypoint
logging.setLoggerClass(MinitrinoLogger)
logger = configure_logging()


class CommandLineInterface(click.MultiCommand):
    """Click MultiCommand class for loading and executing commands."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List available commands."""
        cmd_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "cmd"))
        commands = [
            filename[:-3].replace("_", "-")
            for filename in os.listdir(cmd_dir)
            if filename.endswith(".py") and not filename.startswith("__")
        ]
        return sorted(commands)

    @utils.exception_handler
    def get_command(self, ctx: click.Context, name: str) -> Any:
        """Load and return the command module."""
        mod_name = name.replace("-", "_")
        try:
            mod = import_module(f"minitrino.cmd.{mod_name}")
        except ModuleNotFoundError:
            suggestion = utils.closest_match_or_error(
                name, self.list_commands(ctx), "command"
            )
            raise UserError(f"Command '{name}' not found. {suggestion}")
        cmd = getattr(mod, "cli", None)
        if cmd is None:
            raise UserError(f"No 'cli' object in {mod_name}")
        return cmd


@click.command(cls=CommandLineInterface)
@click.option(
    "--version",
    is_flag=True,
    help="Show the version and exit.",
    expose_value=False,
    is_eager=True,
    callback=lambda ctx, param, value: display_version(ctx) if value else None,
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
@click.option(
    "--log-level",
    type=click.Choice(
        ["ERROR", "WARN", "INFO", "DEBUG"],
        case_sensitive=False,
    ),
    default="INFO",
    help="Set the minimum log level (ERROR, WARN, INFO, DEBUG).",
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
    ctx: MinitrinoContext,
    verbose: bool,
    log_level: str,
    env: list[str],
    cluster_name: str,
) -> None:
    """Welcome to the Minitrino command line interface.

    To report issues or contribute, please visit:
    https://github.com/jefflester/minitrino
    """
    ctx._user_env_args = env
    ctx.cluster_name = cluster_name

    # 1) determine effective log level, 2) configure and set the
    # context's logger, and 3) set the user log level
    effective_log_level = LogLevel.DEBUG if verbose else LogLevel[log_level.upper()]
    ctx.logger = configure_logging(effective_log_level)
    ctx.user_log_level = effective_log_level


def display_version(ctx: click.Context) -> None:
    """Return the version of the CLI and the library as a string."""
    env = []
    args = sys.argv
    i = 0
    while i < len(args):
        if args[i] == "--env" or args[i] == "-e":
            if i + 1 < len(args):
                env.append(args[i + 1])
            i += 2
        else:
            i += 1
    minitrino_ctx: MinitrinoContext = ctx.ensure_object(MinitrinoContext)
    minitrino_ctx._user_env_args = env
    minitrino_ctx.initialize(version_only=True)
    cli_version = utils.cli_ver()
    try:
        lib_version = utils.lib_ver(ctx=minitrino_ctx)
    except Exception:
        lib_version = "NOT INSTALLED"
    minitrino_ctx.logger.info(f"{cli_version} (library: {lib_version})")
    sys.exit()
