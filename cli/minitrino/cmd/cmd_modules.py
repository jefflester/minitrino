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
    """Version command for Minitrino."""

    utils.check_lib(ctx)

    ctx.logger.log("Printing module metadata...")

    if modules and not running:
        for module in modules:
            module_dict = ctx.modules.data.get(module, {})
            if not module_dict:
                raise err.UserError(
                    f"Invalid module: {module}",
                    "Ensure the module you're referencing is in the Minitrino library.",
                )
            log_info(module, module_dict, json_format)
    else:
        if running:
            for module_key, module_dict in ctx.modules.get_running_modules().items():
                for i, container in enumerate(module_dict.get("containers", {})):
                    module_dict["containers"][i] = {
                        "id": container.short_id,
                        "name": container.name,
                        "labels": container.labels,
                    }
                log_info(module_key, module_dict, json_format)
        else:
            for module_key, module_dict in ctx.modules.data.items():
                log_info(module_key, module_dict, json_format)


@pass_environment
def log_info(ctx, module_name="", module_dict={}, json_format=False):
    """Logs module metadata to the user's terminal."""

    if json_format:
        module_dict = {module_name: module_dict}
        ctx.logger.log(json.dumps(module_dict, indent=2))
    else:
        log_msg = [f"Module: {module_name}\n"]
        keys = ["description", "incompatibleModules", "enterprise"]
        for k, v in module_dict.items():
            if k in keys:
                log_msg.extend(f"{k.title()}: {v}\n")

        ctx.logger.log("".join(log_msg))
