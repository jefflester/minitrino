#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import click
import json

from minitrino.cli import pass_environment
from minitrino import errors as err
from minitrino import utils


@click.command(
    "modules",
    help=("""Display module metadata."""),
)
@click.option(
    "-m",
    "--module",
    "modules",
    default=[],
    type=str,
    multiple=True,
    help=("""A specific module to display metadata for."""),
)
@click.option(
    "-j",
    "--json",
    "json_format",
    is_flag=True,
    default=False,
    help=(
        """Print the resulting metadata in JSON form (shows additional module
        metadata)."""
    ),
)
@click.option(
    "-r",
    "--running",
    is_flag=True,
    default=False,
    help=("""Print metadata for all running modules."""),
)
@utils.exception_handler
@pass_environment
def cli(ctx, modules, json_format, running):
    """Module metadata command for Minitrino."""

    utils.check_lib(ctx)

    ctx.logger.info("Printing module metadata...")

    if not modules and not running:
        for module, module_dict in ctx.modules.data.items():
            log_info(module, module_dict, json_format)
        return

    if running:
        modules = ctx.modules.get_running_modules()

    for module in modules:
        module_dict = ctx.modules.data.get(module, {})
        if not module_dict:
            raise err.UserError(
                f"Invalid module: '{module}'",
                "Ensure the module you're referencing is in the Minitrino library.",
            )
        log_info(module, module_dict, json_format)


@pass_environment
def log_info(ctx, module_name="", module_dict={}, json_format=False):
    """Logs module metadata to the user's terminal."""

    if json_format:
        module_dict = {module_name: module_dict}
        ctx.logger.info(json.dumps(module_dict, indent=2))
    else:
        log_msg = [f"Module: {module_name}\n"]
        keys = ["description", "incompatibleModules", "dependentModules", "enterprise"]
        for key in keys:
            val = module_dict.get(key, None)
            if val is not None:
                key = list(key)
                key[0] = key[0].title()
                key = "".join(key)
                log_msg.extend(f"{key}: {val}\n")

        ctx.logger.info("".join(log_msg))
