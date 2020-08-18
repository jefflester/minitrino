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
import yaml
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
        True, compose_environment.compose_env_dict, compose_command
    )

    containers_to_restart = execute_bootstraps(catalog_yaml_files, security_yaml_files)
    if handle_config_properties(catalog_yaml_files, security_yaml_files):
        containers_to_restart.append("presto")
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
def handle_config_properties(ctx, catalog_yaml_files=[], security_yaml_files=[]):
    """
    Loads Presto configuration properties as defined in the YAML file.

    Returns `True` if any provisioned module called for changes to the Presto
    config.properties file and `False` if not.
    """

    executor = CommandExecutor(ctx)
    executor.execute_commands(
        True,
        {},
        f"docker cp presto:/usr/lib/presto/etc/config.properties {ctx.minipresto_user_dir}",
    )

    host_presto_config_file = os.path.join(ctx.minipresto_user_dir, "config.properties")

    yaml_files = catalog_yaml_files + security_yaml_files
    all_config_props = {}
    for yaml_file in yaml_files:
        with open(yaml_file) as f:
            yaml_dict = yaml.load(f, Loader=yaml.FullLoader)
            config_props = recursive_yaml_lookup("CONFIG_PROPERTIES", yaml_dict)
            if config_props is not None:
                config_props = parse_config_props(config_props)
                all_config_props = merge_config_props(all_config_props, config_props)

    if all_config_props == {}:
        return

    existing_config_props = {}
    try:
        with open(host_presto_config_file, "r") as f:
            for line in f:
                line = line.strip().split("=")
                if len(line) != 2:
                    continue
                existing_config_props[line[0].strip()] = line[1].strip()
        all_config_props = merge_config_props(all_config_props, config_props)
    except EnvironmentError as error:
        ctx.log_err(
            f"Error opening existing config.properties file copied from Presto container: {error}"
        )
        sys.exit(1)

    for key, value in all_config_props.items():
        with open(host_presto_config_file, "a") as f:
            f.write(f"{key.strip()}={value.strip()}\n")

    executor.execute_commands(
        True,
        {},
        f"docker cp {host_presto_config_file} presto:/usr/lib/presto/etc/config.properties",
    )
    executor.execute_commands(
        True,
        {},
        f"docker exec -it presto sudo chown presto:presto /usr/lib/presto/etc/config.properties",
    )
    os.remove(host_presto_config_file)
    return True


def recursive_yaml_lookup(key, yaml_dict):
    """
    Performs a recursive key lookup for a nested YAML dictionary. Returns the
    value for the first instance of the key.
    """

    if key in yaml_dict:
        return yaml_dict[key]
    for value in yaml_dict.values():
        if isinstance(value, dict):
            return recursive_yaml_lookup(key, value)
    return None


@pass_environment
def parse_config_props(ctx, config_props={}):
    """Parses string of config properties from a module's YAML file and returns a dict."""

    config_props = config_props.split("\n")
    config_props_dict = {}
    for config_prop in config_props:
        config_prop = config_prop.strip().split("=")
        if config_props_dict.get(
            config_prop[0], True
        ):  # Returns `False` if the property is already in our dict
            config_props_dict[config_prop[0].strip()] = config_prop[1].strip()
    return config_props_dict


@pass_environment
def merge_config_props(ctx, all_config_props={}, config_props={}):
    """
    Merges two dictionaries of config properties and removes duplicate keys.

    Returns the merged dictionary.
    """

    delete = []
    for key, value in config_props.items():
        for key_all, value_all in all_config_props.items():
            if key == key_all:
                delete.append(key)
    for delete_key in delete:
        del config_props[delete_key]

    all_config_props.update(config_props)
    return all_config_props


@pass_environment
def execute_bootstraps(ctx, catalog_yaml_files=[], security_yaml_files=[]):
    """
    Executes bootstrap script for each service that has it. After each script
    executes, the relevant container is restarted.

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
                continue
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
            execute_bootstrap(bootstrap, container_name, service[1])
            containers.append(container_name)
    return containers


@pass_environment
def execute_bootstrap(ctx, bootstrap, container_name, yaml_file):
    """Executes a single bootstrap for a Docker service."""

    bootstrap_file = os.path.join(os.path.dirname(yaml_file), "resources", bootstrap)
    if not os.path.isfile(bootstrap_file):
        ctx.log_err(f"Bootstrap file does not exist: {bootstrap_file}")
        sys.exit(1)

    # Add executable permissions to bootstrap
    st = os.stat(bootstrap_file)
    os.chmod(
        bootstrap_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )
    executor = CommandExecutor(ctx)
    executor.execute_commands(
        True, {}, f"docker cp {bootstrap_file} {container_name}:/"
    )
    executor.execute_commands(
        True,
        {},
        f"docker exec -it {container_name} /{os.path.basename(bootstrap_file)}",
    )
    executor.execute_commands(
        True,
        {},
        f"docker exec -it {container_name} rm /{os.path.basename(bootstrap_file)}",
    )


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
