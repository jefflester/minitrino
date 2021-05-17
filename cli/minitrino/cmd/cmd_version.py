#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import click
from minitrino.cli import pass_environment
from minitrino import utils


@click.command(
    "version",
    help=("""Display Minitrino CLI and library versions."""),
)
@utils.exception_handler
@pass_environment
def cli(ctx):
    """Version command for Minitrino."""

    cli_version = utils.get_cli_ver()
    ctx.logger.log(f"Minitrino version: {cli_version}")

    try:
        lib_version = utils.get_lib_ver(ctx.minitrino_lib_dir)
        ctx.logger.log(f"Library version: {lib_version}")
    except:
        ctx.logger.log("Library version: NOT INSTALLED")
