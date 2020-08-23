#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# Instead of using the Docker SDK, this script will form a Docker Compose
# command string to execute straight through the docker-compose CLI. This is
# required because the Docker SDK does not support communication with Compose
# files.

import os
import sys
import docker
import stat
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

    docker_client = check_daemon()
    catalog, security, env = convert_MultiArgOption_to_list(catalog, security, env)

    catalog_paths = []
    security_paths = []
    catalog_yaml_files, security_yaml_files = validate(catalog, security)

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
        environment=compose_environment.compose_env_dict, commands=[compose_command]
    )

    containers_to_restart = execute_bootstraps(catalog_yaml_files, security_yaml_files)
    handle_config_properties()
    restart_containers(docker_client, containers_to_restart)
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

    Returns file paths to passed in catalog and security modules.
    """

    _, catalog_yaml_files = validate_module_dirs(
        {"module_type": MODULE_CATALOG}, catalog
    )
    _, security_yaml_files = validate_module_dirs(
        {"module_type": MODULE_SECURITY}, security
    )
    return catalog_yaml_files, security_yaml_files


@pass_environment
def execute_bootstraps(ctx, catalog_yaml_files=[], security_yaml_files=[]):
    """
    Executes bootstrap script for each service that has one. After each script
    executes, the relevant container is added to a restart list.

    Returns a list of containers names which had bootstrap scripts executed
    inside of them.
    """

    yaml_files = catalog_yaml_files + security_yaml_files
    services = []
    for yaml_file in yaml_files:
        with open(yaml_file) as f:
            yaml_dict = yaml.load(f, Loader=yaml.FullLoader)
            yaml_dict = yaml_dict.get("services")
            if yaml_dict is None:
                ctx.log_err(
                    f"Invalid Docker Compose YAML file (no 'services' section found): {yaml_file}"
                )
                sys.exit(1)
            for service in yaml_dict.items():
                services.append([service, yaml_file])

    containers = []
    for service in services:
        service_dict = service[0]
        env_vars = service_dict[1].get("environment")
        if env_vars is not None:
            bootstrap = env_vars.get("MINIPRESTO_BOOTSTRAP")
            if bootstrap is None:
                continue
            container_name = service_dict[1].get("container_name")
            if container_name is None:
                container_name = service_dict[0]
            execute_container_bootstrap(bootstrap, container_name, service[1])
            containers.append(container_name)
    return containers


@pass_environment
def execute_container_bootstrap(ctx, bootstrap, container_name, yaml_file):
    """Executes a single bootstrap inside a container."""

    bootstrap_file = os.path.join(os.path.dirname(yaml_file), "resources", bootstrap)
    if not os.path.isfile(bootstrap_file):
        ctx.log_err(f"Bootstrap file does not exist: {bootstrap_file}")
        sys.exit(1)

    # Add executable permissions to bootstrap
    st = os.stat(bootstrap_file)
    os.chmod(
        bootstrap_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )

    ctx.vlog(f"Executing bootstrap script in container: {container_name}")
    executor = CommandExecutor(ctx)
    executor.execute_commands(
        commands=[
            f"docker cp {bootstrap_file} {container_name}:/tmp/",
            f"docker exec -i {container_name} /tmp/{os.path.basename(bootstrap_file)}",
        ]
    )


@pass_environment
def handle_config_properties(ctx):
    """
    Checks for and removes duplicates in the Presto config.properties file.
    """

    ctx.vlog("Checking config.properties for duplicate properties")
    executor = CommandExecutor(ctx)
    executor.execute_commands(
        commands=[
            f"docker cp presto:/usr/lib/presto/etc/config.properties {ctx.minipresto_user_dir}"
        ]
    )

    host_presto_config_file = os.path.join(ctx.minipresto_user_dir, "config.properties")
    config_props = {}

    if not os.path.isfile(host_presto_config_file):
        ctx.log_err(f"config.properties file improperly copied from Presto container")
        sys.exit(1)

    with open(host_presto_config_file, "r") as f:
        for line in f:
            line_list = line.strip().split("=")
            if len(line_list) != 2:
                continue
            # This will return `False` if the property is not already in our dict
            if not config_props.get(line_list[0].strip(), False):
                config_props[line_list[0].strip()] = line_list[1].strip()
            else:
                ctx.log_warn(
                    f"Found duplicate property key in config.properties file:\n"
                    f"{line.strip()}\n"
                    f"{line_list[0].strip()}={config_props.get(line_list[0].strip(), '')}\n"
                )
    os.remove(host_presto_config_file)


@pass_environment
def restart_containers(ctx, docker_client, containers_to_restart=[]):
    """Restarts all the containers in the list."""

    if containers_to_restart == []:
        return

    # Remove any duplicates
    containers_to_restart = list(set(containers_to_restart))

    for container in containers_to_restart:
        try:
            container = docker_client.containers.get(container)
            ctx.vlog(f"Restarting container: {container.name}")
            container.restart()
        except docker.errors.NotFound as error:
            ctx.log_err(
                f"Attempting to restart container {container.name}, but the container was not found"
            )
            sys.exit(1)
