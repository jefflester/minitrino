#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import click
import pkg_resources
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

    version = pkg_resources.require("Minipresto")[0].version
    ctx.logger.log(f"Minipresto version: {version}")
