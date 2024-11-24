#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import click
import json

from minitrino.cli import pass_environment
from minitrino import errors as err
from minitrino import utils
from minitrino.settings import MODULE_ADMIN
from minitrino.settings import MODULE_CATALOG
from minitrino.settings import MODULE_SECURITY


@click.command(
    "modules",
    help="Display module metadata.",
)
@click.option(
    "-m",
    "--module",
    "modules",
    default=[],
    type=str,
    multiple=True,
    help="A specific module to display metadata for.",
)
@click.option(
    "-t",
    "--type",
    "module_type",
    default="",
    type=str,
    help="A module type to display metadata for (admin, catalog, or security).",
)
@click.option(
    "-j",
    "--json",
    "json_format",
    is_flag=True,
    default=False,
    help=(
        f"Print the resulting metadata in raw JSON format "
        f"(shows additional module metadata)."
    ),
)
@click.option(
    "-r",
    "--running",
    is_flag=True,
    default=False,
    help="Print metadata for all running modules.",
)
@utils.exception_handler
@pass_environment
def cli(ctx, modules, module_type, json_format, running):
    """Module metadata command for Minitrino."""

    utils.check_lib(ctx)
    ctx.logger.verbose("Printing module metadata...")

    valid_types = {MODULE_ADMIN, MODULE_CATALOG, MODULE_SECURITY}
    if module_type and module_type not in valid_types:
        raise err.UserError(
            f"Invalid module type: '{module_type}'",
            f"Valid types are: {', '.join(valid_types)}.",
        )

    if running:
        modules_to_process = ctx.modules.get_running_modules()
    elif modules:
        modules_to_process = modules
    else:
        modules_to_process = ctx.modules.data.keys()

    # Filter and display modules
    filtered_modules = filter_modules(ctx, modules_to_process, module_type)
    if not filtered_modules:
        ctx.logger.info("No modules match the specified criteria.")
        return

    for module, module_dict in filtered_modules.items():
        log_info(ctx, module, module_dict, json_format)


def filter_modules(ctx, modules, module_type):
    """
    Filters modules based on their type and returns a dictionary of valid
    modules.
    """
    result = {}
    for module in modules:
        module_dict = ctx.modules.data.get(module)
        if not module_dict:
            continue  # Skip invalid modules silently
        if module_type and module_dict.get("type") != module_type:
            continue  # Skip modules that don't match the specified type
        result[module] = module_dict
    return result


def log_info(ctx, module_name, module_dict, json_format):
    """Logs module metadata to the user's terminal."""
    if json_format:
        print(json.dumps({module_name: module_dict}, indent=2))
    else:
        log_msg = [f"Module: {module_name}\n"]
        keys = [
            "description",
            "incompatibleModules",
            "dependentModules",
            "versions",
            "enterprise",
        ]
        for key in keys:
            val = module_dict.get(key, None)
            if val is not None:
                key = list(key)
                key[0] = key[0].title()
                key = "".join(key)
                log_msg.extend(f"{key}: {val}\n")

        ctx.logger.info("".join(log_msg))
