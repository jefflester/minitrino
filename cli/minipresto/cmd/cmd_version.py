#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import click
from minipresto.cli import pass_environment
from minipresto import utils


@click.command(
    "version",
    help=("""Display the Minipresto version."""),
)
@utils.exception_handler
@pass_environment
def cli(ctx):
    """Version command for Minipresto."""

    version = utils.get_cli_ver()
    ctx.logger.log(f"Minipresto version: {version}")
