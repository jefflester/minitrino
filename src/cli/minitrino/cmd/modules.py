#!/usr/bin/env python3

import click
import json
from typing import Optional

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import UserError
from minitrino.settings import MODULE_ADMIN, MODULE_CATALOG, MODULE_SECURITY


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
    help="Module to display metadata for.",
)
@click.option(
    "-t",
    "--type",
    "module_type",
    default="",
    type=str,
    help="Module type (admin, catalog, or security).",
)
@click.option(
    "-j",
    "--json",
    "json_format",
    is_flag=True,
    default=False,
    help="Output verbose metadata in raw JSON format.",
)
@click.option(
    "-r",
    "--running",
    is_flag=True,
    default=False,
    help=(
        """
        Get metadata for all running modules. By default, applies to 'default'
        cluster.

        Return a list of running modules in specific cluster by using the
        `CLUSTER_NAME` environment variable or the `--cluster` / `-c` option,
        e.g.: 

        `minitrino -c my-cluster modules --running`, or get all running
        modules:\n `minitrino -c all modules --running`"""
    ),
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext,
    modules: list[str],
    module_type: str,
    json_format: bool,
    running: bool,
) -> None:
    """
    Displays Minitrino module metadata.

    Supports filtering by module name, type, or running state. Output can be
    formatted as human-readable logs or raw JSON.

    Parameters
    ----------
    `modules` : `list[str]`
        One or more modules to display metadata for.
    `module_type` : `str`
        Filter results by module type (e.g., admin, catalog, security).
    `json_format` : `bool`
        If True, displays metadata in raw JSON format.
    `running` : `bool`
        If True, displays metadata for only running modules.
    """

    utils.check_lib(ctx)
    ctx.logger.verbose("Printing module metadata...")

    valid_types = {MODULE_ADMIN, MODULE_CATALOG, MODULE_SECURITY}
    if module_type and module_type not in valid_types:
        raise UserError(
            f"Invalid module type: '{module_type}'",
            f"Valid types are: {', '.join(valid_types)}.",
        )

    if running:
        modules_to_process = list(ctx.modules.running_modules().keys())
    elif modules:
        modules_to_process = modules
    else:
        modules_to_process = list(ctx.modules.data.keys())

    # Filter and display modules
    filtered_modules = filter_modules(modules_to_process, module_type)
    if not filtered_modules:
        ctx.logger.info(
            f"No modules match the specified criteria"
            f"{' (type: ' + module_type + ')' if module_type else ''}."
        )
        return

    for module, module_metadata in sorted(filtered_modules.items()):
        log_info(module, module_metadata, json_format)


@utils.pass_environment()
def filter_modules(
    ctx: MinitrinoContext, modules: list[str], module_type: Optional[str]
) -> dict[str, dict]:
    """
    Filters the given modules by the specified type.

    Parameters
    ----------
    `modules` : `list[str]`
        A list of modules to filter.
    `module_type` : `str`, optional
        Optional module type to match against.

    Returns
    -------
    `dict[str, dict]`
        A dictionary of filtered modules and their metadata.
    """
    result = {}
    for module in modules:
        module_metadata = ctx.modules.data.get(module)
        if not module_metadata:
            raise UserError(f"Module '{module}' not found.")
        if module_type and module_metadata.get("type") != module_type:
            continue
        result[module] = module_metadata
    return result


@utils.pass_environment()
def log_info(
    ctx: MinitrinoContext, module_name: str, module_metadata: dict, json_format: bool
) -> None:
    """
    Logs module metadata to the terminal.

    If `json_format` is enabled, outputs raw JSON. Otherwise, prints
    human-readable key information.

    Parameters
    ----------
    `module_name` : `str`
        Name of the module being logged.
    `module_metadata` : `dict`
        Metadata associated with the module.
    `json_format` : `bool`
        If True, displays the output as formatted JSON.
    """
    if json_format:
        print(json.dumps({module_name: module_metadata}, indent=2))
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
            val = module_metadata.get(key, None)
            if val is not None:
                log_msg.append(f"{key[0].upper() + key[1:]}: {val}\n")

        ctx.logger.info("".join(log_msg))
