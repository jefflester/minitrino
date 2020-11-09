#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import click

from minipresto import settings
from minipresto import components

from pathlib import Path

CONTEXT_SETTINGS = {"auto_envvar_prefix": "MINIPRESTO"}

pass_environment = click.make_pass_decorator(components.Environment, ensure=True)


class CommandLineInterface(click.MultiCommand):
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


@click.command(cls=CommandLineInterface, context_settings=CONTEXT_SETTINGS)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help=("""Enable verbose output."""),
)
@click.option(
    "-e",
    "--env",
    default=[],
    type=str,
    multiple=True,
    help=(
        """Add or override environment variables. 

        Environment variables are sourced from the Minipresto library's root
        'minipresto.env' file as well as the user config file in
        '~/.minipresto/minipresto.cfg'. Variables supplied by this option will
        override values from either of those sources. The variables will also be
        passed to the environment of the shell executing commands during the
        'provision' command."""
    ),
)
@pass_environment
def cli(ctx, verbose, env):
    """Welcome to the Minipresto command line interface.

    To report issues and ask questions, please file a GitHub issue and apply a
    descriptive label at the GitHub repository:
    https://github.com/jefflester/minipresto
    """

    ctx._user_init(verbose, env)
