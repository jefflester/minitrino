"""Configuration commands for Minitrino CLI.

Handle configuration-related CLI commands.
"""

import os
import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.settings import CONFIG_TEMPLATE


@click.command(
    "config",
    help="Edit the Minitrino config file (minitrino.cfg).",
)
@click.option(
    "-r",
    "--reset",
    is_flag=True,
    default=False,
    help="Reset the config file with default values.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(ctx: MinitrinoContext, reset: bool) -> None:
    """
    Edit or reset the Minitrino config file.

    Parameters
    ----------
    reset : bool
        If True, resets the config file with default values.
    """
    if os.path.isfile(ctx.config_file) and not reset:
        ctx.logger.verbose(
            f"Opening existing config file at path: {ctx.config_file}",
        )
        edit_file(ctx)
    elif os.path.isfile(ctx.config_file) and reset:
        response = ctx.logger.prompt_msg(f"Configuration file exists. Overwrite? [Y/N]")
        if utils.validate_yes(response):
            write_template(ctx)
            edit_file(ctx)
        else:
            ctx.logger.info(f"Opted out of recreating {ctx.minitrino_user_dir} file.")
    else:
        ctx.logger.verbose(
            f"No config file found at path: {ctx.config_file}. "
            f"Creating template config file and opening for edits...",
        )
        write_template(ctx)
        edit_file(ctx)


@utils.pass_environment()
def write_template(ctx: MinitrinoContext) -> None:
    """Write a template configuration file for the user."""
    with open(ctx.config_file, "w") as config_file:
        config_file.write(CONFIG_TEMPLATE.lstrip())


@utils.pass_environment()
def edit_file(ctx: MinitrinoContext) -> None:
    """Open the config file for editing."""
    editor = ctx.env.get("TEXT_EDITOR") or None
    click.edit(
        filename=ctx.config_file,
        editor=editor,
    )
