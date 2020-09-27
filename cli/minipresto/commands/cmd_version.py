#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import sys
import click
import pkg_resources

from minipresto.cli import pass_environment


# fmt: off
@click.command("version", help="""
Display the Minipresto version.
""")
# fmt: on


@pass_environment
def cli(ctx):
    """Version command for Minipresto."""

    version = pkg_resources.require("Minipresto")[0].version
    ctx.log(f"Minipresto version: {version}")
