#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# Instead of using the Docker SDK, this script will form a Docker Compose
# command string to execute straight through the docker-compose CLI. This is
# required because the Docker SDK does not support communication with Compose
# files.

import os
import sys
import click

from minipresto.cli import pass_environment
from minipresto.commands.core import MultiArgOption
from minipresto.commands.core import CommandExecutor
from minipresto.commands.core import ComposeEnvironment
from minipresto.commands.core import check_daemon
from minipresto.commands.core import convert_MultiArgOption_to_list
from minipresto.commands.core import validate_module_dirs

from minipresto.settings import MODULE_ROOT
from minipresto.settings import MODULE_CATALOG
from minipresto.settings import MODULE_SECURITY


@click.command("provision", help="""
Provisions an environment based on chosen modules. All options are optional and
can be left empty. 
""")
@click.option("-c", "--catalog", default="", type=str, cls=MultiArgOption, help="""
Catalog modules to provision. 
""")
@click.option("-s", "--security", default="", type=str, cls=MultiArgOption, help="""
Security modules to provision. 
""")
@click.option("-e", "--env", default="", type=str, cls=MultiArgOption, help="""
Overrides a pre-defined environment variable(s). Can override config in the user's
`minipresto.cfg` file and the library's `.env` file.
""")
@click.option("-d", "--docker-native", default="", type=str, help="""
Appends native docker-compose commands to the built docker-compose command. Run
`docker-compose up --help` to see all available options.

Example: minipresto provision -d --build

Example: minipresto provision -d '--remove-orphans --force-recreate'
""")


@pass_environment
def cli(ctx, catalog, security, env, docker_native):
    """
    Provision command for minipresto. If the resulting docker-compose command
    is unsuccessful, the function exits with a non-zero status code.
    """

    check_daemon()
    catalog, security, env = convert_MultiArgOption_to_list(catalog, security, env)
    validate(catalog, security)

    catalog_chunk = compose_chunk(catalog, {"module_type": "catalog"})
    security_chunk = compose_chunk(security, {"module_type": "security"})

    if all((not catalog_chunk, not security_chunk)):
        ctx.log(
            f"No catalog or security options received. Provisioning standalone Presto container"
        )

    compose_environment = ComposeEnvironment(ctx, env)
    compose_command = compose_builder(
        docker_native,
        compose_environment.compose_env_string,
        catalog_chunk,
        security_chunk,
    )

    executor = CommandExecutor(ctx)
    executor.execute_commands(
        True, compose_environment.compose_env_dict, compose_command
    )
    ctx.log(f"Environment provisioning complete")


@pass_environment
def compose_chunk(ctx, items=[], key={}):
    """
    Builds docker-compose command chunk for chosen modules. Command chunks are
    compatible with the docker-compose CLI. Returns a command chunk string.
    """

    if not items:
        return ""

    module_type = key.get("module_type", "")
    command_chunk = []

    for i in range(len(items)):
        compose_path = os.path.abspath(
            os.path.join(
                ctx.minipresto_lib_dir,
                MODULE_ROOT,
                module_type,
                items[i],
                items[i] + ".yml",
            )
        )

        compose_path_formatted = f"-f {compose_path} \\\n"
        command_chunk.append(compose_path_formatted)

    return "".join(command_chunk)


@pass_environment
def compose_builder(ctx, docker_native="", compose_env="", *args):
    """
    Builds a formatted docker-compose command for shell execution from provided
    command chunks. Returns a full docker-compose command string.
    """

    command = []
    command.extend(
        [
            compose_env,
            "\\\n",
            "docker-compose -f ",
            os.path.abspath(os.path.join(ctx.minipresto_lib_dir, "docker-compose.yml")),
            " \\\n",
        ]
    )

    for arg in args:
        command.append(arg)

    command.append("up -d")

    if docker_native:
        ctx.vlog(f"Received native Docker Compose options")
        command.extend([" ", docker_native])

    return "".join(command)


def validate(catalog=[], security=[]):
    """
    Validates module input and ensures that the chosen modules map to a valid
    directory and YAML file.
    """

    validate_module_dirs({"module_type": MODULE_CATALOG}, catalog)
    validate_module_dirs({"module_type": MODULE_SECURITY}, security)
