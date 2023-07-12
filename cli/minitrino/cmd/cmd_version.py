#!usr/bin/env/python3
# -*- coding: utf-8 -*-

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
    ctx.logger.info(f"Minitrino version: {cli_version}")

    try:
        lib_version = utils.get_lib_ver(ctx.minitrino_lib_dir)
        ctx.logger.info(f"Library version: {lib_version}")
    except:
        ctx.logger.info("Library version: NOT INSTALLED")
