#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import click
import shutil

from minipresto.cli import pass_environment
from minipresto.commands.core import validate_yes_response

from minipresto.settings import CONFIG_TEMPLATE


@click.command("config", help="""
Sets minipresto user configuration.
""")
@click.option("-r", "--reset", is_flag=True, default=False, help="""
Resets minipresto user configuration directory and creates template config
file.
""")


@pass_environment
def cli(ctx, reset):
    """Config command for minipresto."""

    if reset:
        __reset()

    if not os.path.isdir(ctx.minipresto_user_dir):
        ctx.log("No .minipresto directory found. Creating")
        os.mkdir(ctx.minipresto_user_dir)

    if os.path.isfile(ctx.config_file):
        ctx.vlog("Opening existing config file")
        click.edit(filename=ctx.config_file)
    else:
        ctx.vlog(
            "No config file found. Creating template config file and opening for edits"
        )
        copy_template_and_edit()


@pass_environment
def __reset(ctx):
    """
    Resets minipresto user configuration directory. If the user configuration
    directory exists, it will prompt the user for approval before overwriting.
    Exits after successful run with a 0 status code.
    """

    try:
        os.mkdir(ctx.minipresto_user_dir)
    except:
        response = ctx.prompt_msg("Configuration directory exists. Overwrite? [Y/N]")
        if validate_yes_response(response):
            shutil.rmtree(ctx.minipresto_user_dir)
            os.mkdir(ctx.minipresto_user_dir)
        else:
            ctx.log("Opted to skip recreating configuration directory")
            sys.exit(0)
    ctx.vlog("Created minipresto configuration directory")

    copy_template_and_edit()
    sys.exit(0)


@pass_environment
def copy_template_and_edit(ctx):
    """
    Copies the configuration template and opens the file for edits.
    """

    with open(ctx.config_file, "w") as config_file:
        config_file.write(CONFIG_TEMPLATE.lstrip())

    click.edit(filename=ctx.config_file)
