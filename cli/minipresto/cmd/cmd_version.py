#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import click
import minipresto.cli
import minipresto.utils as utils


# fmt: off
@click.command("version", help="""
Display the Minipresto version.
""")
# fmt: on


@utils.exception_handler
@minipresto.cli.pass_environment
def cli(ctx):
    """Version command for Minipresto."""

    version = utils.get_cli_ver()
    ctx.logger.log(f"Minipresto version: {version}")
