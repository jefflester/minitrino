"""Commands for displaying and filtering Minitrino module metadata."""

import json
import sys
from typing import Optional

import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import UserError
from minitrino.core.logger import LogLevel
from minitrino.settings import MODULE_ADMIN, MODULE_CATALOG, MODULE_SECURITY


@click.command(
    "modules",
    help="Get module metadata.",
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
    help="Output module metadata in JSON.",
)
@click.option(
    "-r",
    "--running",
    is_flag=True,
    default=False,
    help="Get metadata for all running modules.",
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
    """Display Minitrino module metadata.

    Supports filtering by module name, type, or running state. Output
    can be formatted as human-readable logs or JSON.

    Parameters
    ----------
    modules : list[str]
        One or more modules to display metadata for.
    module_type : str
        Filter results by module type (e.g., admin, catalog, security).
    json_format : bool
        If True, displays metadata in JSON format.
    running : bool
        If True, displays metadata for only running modules.
    """
    if json_format:
        ctx.initialize(log_level=LogLevel.ERROR)
    else:
        ctx.initialize()

    utils.check_lib(ctx)
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

    if json_format:
        all_metadata = {
            module: module_metadata
            for module, module_metadata in sorted(filtered_modules.items())
        }
        sys.stdout.write(json.dumps(all_metadata, indent=2) + "\n")
    else:
        for module, module_metadata in sorted(filtered_modules.items()):
            log_info(module, module_metadata)


@utils.pass_environment()
def filter_modules(
    ctx: MinitrinoContext, modules: list[str], module_type: Optional[str]
) -> dict[str, dict]:
    """Filter the given modules by the specified type.

    Parameters
    ----------
    modules : list[str]
        A list of modules to filter.
    module_type : str, optional
        Optional module type to match against.

    Returns
    -------
    dict[str, dict]
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
def log_info(ctx: MinitrinoContext, module_name: str, module_metadata: dict) -> None:
    """Log module metadata to the terminal.

    Parameters
    ----------
    ctx : MinitrinoContext
        The current Minitrino context.
    module_name : str
        Name of the module being logged.
    module_metadata : dict
        Metadata associated with the module.
    """

    log_msg = [f"Module: {module_name}\n"]
    keys = [
        "description",
        "incompatibleModules",
        "dependentModules",
        "versions",
        "enterprise",
        "dependentClusters",
    ]
    for key in keys:
        val = module_metadata.get(key, None)
        if val is not None:
            try:
                val = json.dumps(val, indent=2)
            except TypeError:
                pass
            log_msg.append(f"{key[0].upper() + key[1:]}: {val}\n")
    ctx.logger.info("".join(log_msg))
