#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import click

import minipresto.cli
import minipresto.utils as utils


# fmt: off
@click.command("config", help="""
Edits Minipresto user configuration.
""")
@click.option("-r", "--reset", is_flag=True, default=False, help="""
Resets Minipresto user configuration directory and creates template config
file.
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
        click.edit(
            filename=ctx.config_file,
            editor=ctx.env.get_var(
                key="TEXT_EDITOR", default=None
            ),
        )
    else:
        ctx.logger.log(
            f"No config file found at path: {ctx.config_file}. "
            f"Creating template config file and opening for edits...",
            level=ctx.logger.verbose,
        )
        copy_template_and_edit()


@minipresto.cli.pass_environment
def _reset(ctx):
    """Resets Minipresto user configuration directory. If the user configuration
    directory exists, it will prompt the user for approval before overwriting.
    Exits after successful run with a 0 status code.
    """

    from shutil import rmtree

    try:
        os.mkdir(ctx.minipresto_user_dir)
    except:
        response = ctx.logger.prompt_msg("Configuration directory exists. Overwrite? [Y/N]")
        if utils.validate_yes(response):
            rmtree(ctx.minipresto_user_dir)
            os.mkdir(ctx.minipresto_user_dir)
        else:
            ctx.logger.log(f"Opted out of recreating {ctx.minipresto_user_dir} directory.")
            sys.exit(0)

    ctx.logger.log("Created Minipresto configuration directory", level=ctx.logger.verbose)
    copy_template_and_edit()
    sys.exit(0)


@minipresto.cli.pass_environment
def copy_template_and_edit(ctx):
    """Copies the configuration template and opens the file for edits."""

    from minipresto.settings import CONFIG_TEMPLATE

    with open(ctx.config_file, "w") as config_file:
        config_file.write(CONFIG_TEMPLATE.lstrip())
    click.edit(filename=ctx.config_file)
