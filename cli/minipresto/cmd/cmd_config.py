#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import click

import minipresto.cli
import minipresto.utils as utils

from shutil import rmtree
from minipresto.settings import CONFIG_TEMPLATE


# fmt: off
@click.command("config", help="""
Edit the Minipresto user configuration file.
""")
@click.option("-r", "--reset", is_flag=True, default=False, help="""
Reset the Minipresto user configuration directory and create a new config file.

WARNING: This will remove your configuration file (if it exists) and replace it
with a template.
""")
# fmt: on


@utils.exception_handler
@minipresto.cli.pass_environment
def cli(ctx, reset):
    """Config command for Minipresto."""

    if reset:
        _reset()

    if not os.path.isdir(ctx.minipresto_user_dir):
        ctx.logger.log(f"No {ctx.minipresto_user_dir} directory found. Creating...")
        os.mkdir(ctx.minipresto_user_dir)

    if os.path.isfile(ctx.config_file):
        ctx.logger.log(
            f"Opening existing config file at path: {ctx.config_file}",
            level=ctx.logger.verbose,
        )
        edit_file()
    else:
        ctx.logger.log(
            f"No config file found at path: {ctx.config_file}. "
            f"Creating template config file and opening for edits...",
            level=ctx.logger.verbose,
        )
        write_template()
        edit_file()


@minipresto.cli.pass_environment
def _reset(ctx):
    """Resets Minipresto user configuration directory. If the user configuration
    directory exists, it will prompt the user for approval before overwriting.
    Exits after successful run with a 0 status code."""

    try:
        os.mkdir(ctx.minipresto_user_dir)
    except:
        response = ctx.logger.prompt_msg(
            f"Configuration directory exists. Overwrite? [Y/N]"
        )
        if utils.validate_yes(response):
            rmtree(ctx.minipresto_user_dir)
            os.mkdir(ctx.minipresto_user_dir)
        else:
            ctx.logger.log(
                f"Opted out of recreating {ctx.minipresto_user_dir} directory."
            )
            sys.exit(0)

    ctx.logger.log(
        "Created Minipresto configuration directory", level=ctx.logger.verbose
    )
    write_template()
    edit_file()
    sys.exit(0)


@minipresto.cli.pass_environment
def write_template(ctx):
    """Writes configuration template."""

    with open(ctx.config_file, "w") as config_file:
        config_file.write(CONFIG_TEMPLATE.lstrip())

    editor = ctx.env.get_var(key="TEXT_EDITOR", default=None)
    if not editor:
        editor = None


@minipresto.cli.pass_environment
def edit_file(ctx):
    """Gets the editor from user configuration and passes to the Click edit
    function if the value is present."""

    editor = ctx.env.get_var(key="TEXT_EDITOR", default=None)
    if not editor:
        editor = None

    click.edit(
        filename=ctx.config_file,
        editor=editor,
    )
