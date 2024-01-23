#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import click

from minitrino import components

pass_environment = click.make_pass_decorator(components.Environment, ensure=True)


class CommandLineInterface(click.MultiCommand):
    def list_commands(self, ctx):
        cmd_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "cmd"))
        retval = []
        for filename in os.listdir(cmd_dir):
            if filename.endswith(".py") and filename.startswith("cmd_"):
                retval.append(filename[4:-3].replace("_", "-"))
        retval.sort()
        return retval

    def get_command(self, ctx, name):
        try:
            mod = __import__(
                f"minitrino.cmd.cmd_{name.replace('-', '_')}", None, None, ["cli"]
            )
        except ImportError:
            return
        return mod.cli


@click.command(cls=CommandLineInterface)
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

        To learn more about environment variables and the order of precedence,
        visit the project wiki at:
        https://github.com/jefflester/minitrino/wiki/Environment-Variables-and-Config"""
    ),
)
@pass_environment
def cli(ctx, verbose, env):
    """Welcome to the Minitrino command line interface.

    To report issues and ask questions, please file a GitHub issue and apply a
    descriptive label at the GitHub repository:
    https://github.com/jefflester/minitrino
    """

    ctx._user_init(verbose, env)
