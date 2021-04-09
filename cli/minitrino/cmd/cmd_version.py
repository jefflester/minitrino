#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import click
from minitrino.cli import pass_environment
from minitrino import utils


@click.command(
    "version",
    help=("""Display the Minitrino version."""),
)
@utils.exception_handler
@pass_environment
def cli(ctx):
    """Version command for Minitrino."""

    version = utils.get_cli_ver()
    ctx.logger.log(f"Minitrino version: {version}")
