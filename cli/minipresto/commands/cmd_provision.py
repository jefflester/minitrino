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
import hashlib
import click

from minipresto.cli import pass_environment
from minipresto.commands.cmd_down import cli as rollback
from minipresto.exceptions import MiniprestoException

from minipresto.core import CommandExecutor
from minipresto.core import ComposeEnvironment
from minipresto.core import handle_exception
from minipresto.core import check_daemon
from minipresto.core import validate_module_dirs

from minipresto.settings import RESOURCE_LABEL
from minipresto.settings import MODULE_ROOT
from minipresto.settings import MODULE_CATALOG
from minipresto.settings import MODULE_SECURITY


@click.command("provision", help="""
Provisions an environment based on chosen modules. All options are optional and
can be left empty. 
""")
@click.option("-c", "--catalog", default=[], type=str, multiple=True, help="""
Catalog module to provision. 
""")
@click.option("-s", "--security", default=[], type=str, multiple=True, help="""
Security module to provision. 
""")
@click.option("-e", "--env", default=[], type=str, multiple=True, help="""
Add or override environment variables. If any of the variables overlap with
variables in the library's `.env` file or the `minipresto.cfg` file, the
variable will be overridden with what is provided in `--env`.
""")
@click.option("-n", "--no-rollback", is_flag=True, default=False, help="""
Do not rollback provisioned resources in the event of an error.
""")
@click.option("-d", "--docker-native", default="", type=str, help="""
Appends native docker-compose commands to the built docker-compose command. Run
`docker-compose up --help` to see all available options.

Example: minipresto provision -d --build

Example: minipresto provision -d '--remove-orphans --force-recreate'
""")


@pass_environment
def cli(ctx, catalog, security, env, no_rollback, docker_native):
    """
    Provision command for Minipresto. If the resulting docker-compose command is
    unsuccessful, the function exits with a non-zero status code.
    """

    check_daemon()

    try:
        catalog_yaml_files, security_yaml_files = validate(catalog, security)
        catalog_chunk = compose_chunk(catalog, {"module_type": "catalog"})
        security_chunk = compose_chunk(security, {"module_type": "security"})

        if all((not catalog_chunk, not security_chunk)):
            ctx.log(
                f"No catalog or security options received. Provisioning standalone Presto container..."
            )

        compose_environment = ComposeEnvironment(ctx, env)
        compose_environment = check_license(compose_environment)
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

        initialize_containers()
        containers_to_restart = execute_bootstraps(
            catalog_yaml_files, security_yaml_files
        )
        handle_config_properties()
        restart_containers(containers_to_restart)
        ctx.log(f"Environment provisioning complete.")

    except MiniprestoException as e:
        rollback_provision(no_rollback)
        handle_exception(e)

    except Exception as e:
        rollback_provision(no_rollback)
        ctx.log_err(f"Error occurred during environment provisioning: {e}")
        sys.exit(1)


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
        ctx.vlog(f"Received native Docker Compose options: '{docker_native}'")
        command.extend([" ", docker_native])

    return "".join(command)


def validate(catalog=[], security=[]):
    """
    Validates module input and ensures that the chosen modules map to a valid
    directory and YAML file.

    Returns file paths to passed in catalog and security modules.
    """

    _, catalog_yaml_files = validate_module_dirs(MODULE_CATALOG, catalog)
    _, security_yaml_files = validate_module_dirs(MODULE_SECURITY, security)
    return catalog_yaml_files, security_yaml_files


@pass_environment
def execute_bootstraps(ctx, catalog_yaml_files=[], security_yaml_files=[]):
    """
    Executes bootstrap script for each container that has one––bootstrap scripts
    will only execute once the container is fully running to prevent conflicts
    with procedures executing as part of the container's entrypoint. After each
    script executes, the relevant container is added to a restart list.

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
                raise MiniprestoException(
                    f"Invalid Docker Compose YAML file (no 'services' section found): {yaml_file}"
                )
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
            if execute_container_bootstrap(bootstrap, container_name, service[1]):
                containers.append(container_name)
    return containers


@pass_environment
def execute_container_bootstrap(
    ctx, bootstrap_basename="", container_name="", yaml_file=""
):
    """
    Executes a single bootstrap inside a container. If the
    `/opt/minipresto/bootstrap_status.txt` file has the same checksum as the
    bootstrap script that is about to be executed, the boostrap script is
    skipped.

    Returns `False` if the script is not executed and `True` if it is.
    """

    bootstrap_file = os.path.join(
        os.path.dirname(yaml_file), "resources", "bootstrap", bootstrap_basename
    )
    if not os.path.isfile(bootstrap_file):
        raise MiniprestoException(
            f"Bootstrap file does not exist at location: {bootstrap_file}"
        )

    # Add executable permissions to bootstrap
    st = os.stat(bootstrap_file)
    os.chmod(
        bootstrap_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )

    executor = CommandExecutor(ctx)
    bootstrap_checksum = hashlib.md5(open(bootstrap_file, "rb").read()).hexdigest()
    container = ctx.docker_client.containers.get(container_name)

    output = executor.execute_commands(
        commands=["cat /opt/minipresto/bootstrap_status.txt"],
        suppress_output=True,
        container=container,
    )
    if f"{bootstrap_checksum}" in output[0].get("output", ""):
        ctx.vlog(
            f"Bootstrap already executed in container '{container_name}'. Skipping."
        )
        return False

    ctx.vlog(f"Executing bootstrap script in container '{container_name}'...")
    executor.execute_commands(
        commands=[f"docker cp {bootstrap_file} {container_name}:/tmp/",]
    )
    executor.execute_commands(
        commands=[
            f"/tmp/{os.path.basename(bootstrap_file)}",
            f'bash -c "echo {bootstrap_checksum} >> /opt/minipresto/bootstrap_status.txt"',
        ],
        container=container,
    )

    ctx.vlog(f"Successfully executed bootstrap script in container '{container_name}'.")
    return True


@pass_environment
def handle_config_properties(ctx):
    """
    Checks for duplicates in the Presto config.properties file and issues
    warnings for any detected duplicates.
    """

    ctx.vlog("Checking Presto config.properties for duplicate properties...")
    executor = CommandExecutor(ctx)
    container = ctx.docker_client.containers.get("presto")
    output = executor.execute_commands(
        commands=["cat /usr/lib/presto/etc/config.properties"],
        suppress_output=True,
        container=container,
    )

    config_props = output[0].get("output", "")
    if not config_props:
        raise MiniprestoException(
            "Presto config.properties file unable to be read from Presto container."
        )

    config_props = config_props.strip().split("\n")
    config_props.sort()
    counter = 0
    while counter < len(config_props):
        config_prop = config_props[counter]
        config_prop = config_prop.strip().split("=")
        key = config_prop[0].strip()

        inner_counter = counter + 1
        duplicates = []
        while inner_counter < len(config_props):
            check_config_prop = config_props[inner_counter].strip().split("=")
            check_key = check_config_prop[0].strip()
            if key == check_key:
                duplicates.append(config_props[inner_counter])
                inner_counter += 1
            else:
                break

        if duplicates:
            duplicates.insert(0, config_props[counter])
            duplicates_string = "\n".join(duplicates)
            ctx.log_warn(
                f"Duplicate Presto configuration properties detected in config.properties file:\n{duplicates_string}"
            )
        counter = inner_counter


@pass_environment
def restart_containers(ctx, containers_to_restart=[]):
    """Restarts all the containers in the list."""

    if containers_to_restart == []:
        return

    # Remove any duplicates
    containers_to_restart = list(set(containers_to_restart))

    for container in containers_to_restart:
        try:
            container = ctx.docker_client.containers.get(container)
            ctx.vlog(f"Restarting container '{container.name}'...")
            container.restart()
        except docker.errors.NotFound as error:
            raise MiniprestoException(
                f"Attempting to restart container '{container.name}', but the container was not found."
            )


@pass_environment
def check_license(ctx, compose_environment={}):
    """
    Checks for Starburst Data license. If no license, creates a placeholder
    license and points to it.
    """

    starburst_lic_file = compose_environment.compose_env_dict.get(
        "STARBURST_LIC_PATH", ""
    ).strip()
    placeholder_lic_file = os.path.join(ctx.minipresto_user_dir, "placeholder.license")

    if starburst_lic_file:
        if not os.path.isfile(starburst_lic_file):
            ctx.vlog(
                f"Starburst license not found at path: {starburst_lic_file}.\n"
                f"Creating placeholder license at path: {placeholder_lic_file}"
            )
            with open(placeholder_lic_file, "w") as f:
                pass
        else:
            return compose_environment

    compose_environment.compose_env_dict["STARBURST_LIC_PATH"] = placeholder_lic_file
    compose_environment.compose_env_string += (
        f'STARBURST_LIC_PATH="{placeholder_lic_file}" '
    )
    if not os.path.isfile(placeholder_lic_file):
        ctx.vlog(f"Creating placeholder license at path: {placeholder_lic_file}")
        with open(placeholder_lic_file, "w") as f:
            pass
    return compose_environment


@pass_environment
def initialize_containers(ctx):
    """
    Initializes each container with /opt/minipresto/bootstrap_status.txt
    """
    executor = CommandExecutor(ctx)
    containers = ctx.docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    for container in containers:
        output = executor.execute_commands(
            commands=["cat /opt/minipresto/bootstrap_status.txt"],
            suppress_output=True,
            container=container,
            handle_error=False,
        )
        output_string = output[0].get("output", "").strip()
        if "no such file or directory" in output_string.lower():
            executor.execute_commands(
                commands=[
                    "mkdir -p /opt/minipresto/",
                    "touch /opt/minipresto/bootstrap_status.txt",
                ],
                container=container,
            )
        elif output[0].get("return_code", None) == 0:
            continue
        else:
            raise MiniprestoException(
                f"Command failed.\n"
                f"Output: {output_string}\n"
                f"Exit code: {output[0].get('return_code', None)}"
            )


@pass_environment
def rollback_provision(ctx, no_rollback):
    """
    Rolls back the provisioning command in the event of an error.
    """

    if no_rollback:
        ctx.log_warn(
            f"Errors occurred during environment provisioning and rollback has been disabled. "
            f"Provisioned resources will remain in an unaltered state."
        )
        sys.exit(1) # Exit with non-zero since provisioning failed

    ctx.log_err(
        f"Rolling back provisioned resources due to "
        f"errors encountered while provisioning the environment."
    )

    rollback(keep=False)
