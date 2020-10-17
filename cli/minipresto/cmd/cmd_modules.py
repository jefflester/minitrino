#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import click
import pkg_resources
import minipresto.cli
import minipresto.errors as err
import minipresto.utils as utils


# fmt: off
@click.command("modules", help="""
Display metadata about Minipresto modules.
""")
@click.option("-m", "--module", "modules", default=[], type=str, multiple=True, help="""
A specific module to display metadata for. 
""")
# fmt: on


@utils.exception_handler
@minipresto.cli.pass_environment
def cli(ctx, modules):
    """Version command for Minipresto."""

    if modules:
        for module in modules:
            module_dict = ctx.modules.data.get(module, {})
            if not module_dict:
                raise err.UserError(
                    f"Invalid module: {module}",
                    "Ensure the module you're referencing is in the Minipresto library.",
                )
            log_info(module, module_dict)
    else:
        for module_key, module_dict in ctx.modules.data.items():
            log_info(module_key, module_dict)


@minipresto.cli.pass_environment
def log_info(ctx, module_name="", module_dict={}):
    """Logs module metadata to the user's terminal."""

    description = module_dict.get("description", "")
    incompatible_modules = module_dict.get("incompatible_modules", [])
    ctx.logger.log(
        f"Module: {module_name}\n"
        f"Description: {description}\n"
        f"Incompatible Modules: {incompatible_modules}",
    )
