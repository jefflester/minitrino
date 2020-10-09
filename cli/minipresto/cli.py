#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import click
import minipresto.components as components

from pathlib import Path

CONTEXT_SETTINGS = dict(auto_envvar_prefix="MINIPRESTO")

pass_environment = click.make_pass_decorator(components.Environment, ensure=True)


class CLI(click.MultiCommand):
    def list_commands(self, ctx):
        cmd_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "cmd"))
        retval = []
        for filename in os.listdir(cmd_dir):
            if filename.endswith(".py") and filename.startswith("cmd_"):
                retval.append(filename[4:-3])
        retval.sort()
        return retval

    def get_command(self, ctx, name):
        try:
            mod = __import__(f"minipresto.cmd.cmd_{name}", None, None, ["cli"])
        except ImportError:
            return
        return mod.cli


# fmt: off
@click.command(cls=CLI, context_settings=CONTEXT_SETTINGS)
@click.option("-v", "--verbose", is_flag=True, default=False, help="""
Enables verbose output.
""")
@click.option("-e", "--env", default=[], type=str, multiple=True, help="""
Add or override environment variables. The variable set is comprised of values
from the Minipresto library's root '.env' file as well as values from the
'minipresto.cfg' file. This option will override existing variables or append
new ones if they don't exist.
""")
# fmt: on


@pass_environment
def cli(ctx, verbose, env):
    """Minipresto command line interface."""

    ctx._user_init(verbose, env)
    ctx.logger.log(
        f"Library path set to: {ctx.minipresto_lib_dir}", level=ctx.logger.verbose
    )
