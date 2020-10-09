#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# Instead of using the Docker SDK, this script will form a Docker Compose
# command string to execute straight through the docker-compose CLI. This is
# required because the Docker SDK does not support communication with Compose
# files, and Minipresto benefits hugely from Docker Compose.

import os
import stat
import hashlib
import click

import minipresto.cli
import minipresto.utils as utils
import minipresto.errors as err

from minipresto.settings import RESOURCE_LABEL
from minipresto.settings import MODULE_ROOT
from minipresto.settings import MODULE_CATALOG
from minipresto.settings import MODULE_SECURITY
from minipresto.settings import ETC_PRESTO

from docker.errors import NotFound


# fmt: off
@click.command("provision", help="""
Provisions an environment based on chosen modules. All options are optional and
can be left empty. 
""")
@click.option("-m", "--module", "modules", default=[], type=str, multiple=True, help="""
A specific module to provision. 
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
# fmt: on


@utils.exception_handler
@minipresto.cli.pass_environment
def cli(ctx, modules, no_rollback, docker_native):
    """Provision command for Minipresto. If the resulting docker-compose command
    is unsuccessful, the function exits with a non-zero status code.
    """

    utils.check_daemon(ctx.docker_client)

    if not modules:
        ctx.logger.log(
            f"No catalog or security options received. Provisioning "
            f"standalone Presto container..."
        )
    else:
        for module in modules:
            if not ctx.modules.data.get(module, False):
                raise err.UserError(
                    f"Invalid module: '{module}'. It was not found "
                    f"in the Minipresto library at {ctx.minipresto_lib_dir}"
                )

    try:
        cmd_chunk = chunk(modules)

        # Module env variables shared with compose should be from the modules
        # section of environment variables and any extra variables provided by the
        # user that didn't fit into any other section

        compose_env = ctx.env.get_section("MODULES")
        compose_env.update(ctx.env.get_section("EXTRA"))
        compose_cmd = build_command(docker_native, compose_env, cmd_chunk)

        ctx.cmd_executor.execute_commands(compose_cmd, environment=compose_env)
        initialize_containers()

        containers_to_restart = execute_bootstraps(modules)
        containers_to_restart = append_user_config(containers_to_restart)
        handle_config_properties()
        restart_containers(containers_to_restart)
        ctx.logger.log(f"Environment provisioning complete.")

    except Exception as e:
        rollback_provision(no_rollback)
        utils.handle_exception(e)


@minipresto.cli.pass_environment
def chunk(ctx, modules=[]):
    """Builds docker-compose command chunk for the chosen modules. Returns a
    command chunk string.
    """

    chunk = []
    for mod in modules:
        yaml_file = ctx.modules.data.get(mod, "").get("yaml_file", "")
        chunk.extend(f"-f {yaml_file} \\\n")
    return "".join(chunk)


@minipresto.cli.pass_environment
def build_command(ctx, docker_native="", compose_env={}, chunk=""):
    """Builds a formatted docker-compose command for shell execution. Returns a
    docker-compose command string.
    """

    cmd = []
    compose_env_string = ""
    for k, v in compose_env.items():
        compose_env_string += f'{k.upper()}="{v}" '

    cmd.extend(
        [
            compose_env_string,
            "\\\n",
            "docker-compose -f ",
            os.path.join(ctx.minipresto_lib_dir, "docker-compose.yml"),
            " \\\n",
            chunk,  # Module YAML paths
            "up -d",
        ]
    )

    if docker_native:
        ctx.logger.log(
            f"Received native Docker Compose options: '{docker_native}'",
            level=ctx.logger.verbose,
        )
        cmd.extend([" ", docker_native])
    return "".join(cmd)


@minipresto.cli.pass_environment
def execute_bootstraps(ctx, modules=[]):
    """Executes bootstrap script for each container that has one––bootstrap
    scripts will only execute once the container is fully running to prevent
    conflicts with procedures executing as part of the container's entrypoint.
    After each script executes, the relevant container is added to a restart
    list.

    Returns a list of containers names which had bootstrap scripts executed
    inside of them.
    """

    services = []
    for module in modules:
        yaml_file = ctx.modules.data.get(module, {}).get("yaml_file", "")
        module_services = (
            ctx.modules.data.get(module, {}).get("yaml_dict", {}).get("services", {})
        )
        if not module_services:
            raise err.MiniprestoError(
                f"Invalid Docker Compose YAML file (no 'services' section found): {yaml_file}"
            )
        for service_key, service_dict in module_services.items():
            services.append([service_key, service_dict, yaml_file])

    containers = []
    for service in services:
        bootstrap = service[1].get("environment", {}).get("MINIPRESTO_BOOTSTRAP")
        if bootstrap is None:
            continue
        container_name = service.get("container_name")
        if container_name is None:
            # If there is not container name, the service name becomes the name
            # of the container
            container_name = service[0]
        if execute_container_bootstrap(bootstrap, container_name, service[2]):
            containers.append(container_name)
    return containers


@minipresto.cli.pass_environment
def execute_container_bootstrap(ctx, bootstrap="", container_name="", yaml_file=""):
    """Executes a single bootstrap inside a container. If the
    `/opt/minipresto/bootstrap_status.txt` file has the same checksum as the
    bootstrap script that is about to be executed, the boostrap script is
    skipped.

    Returns `False` if the script is not executed and `True` if it is.
    """

    if any((not bootstrap, not container_name, not yaml_file)):
        raise utils.handle_missing_param(list(locals().keys()))

    bootstrap_file = os.path.join(
        os.path.dirname(yaml_file), "resources", "bootstrap", bootstrap
    )
    if not os.path.isfile(bootstrap_file):
        raise err.UserError(
            f"Bootstrap file does not exist at location: {bootstrap_file}",
            "Check this module in the library to ensure the bootstrap script is present.",
        )

    # Add executable permissions to bootstrap
    st = os.stat(bootstrap_file)
    os.chmod(
        bootstrap_file,
        st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )

    bootstrap_checksum = hashlib.md5(open(bootstrap_file, "rb").read()).hexdigest()
    container = ctx.docker_client.containers.get(container_name)

    output = ctx.cmd_executor.execute_commands(
        "cat /opt/minipresto/bootstrap_status.txt",
        suppress_output=True,
        container=container,
        trigger_error=False,
    )
    if f"{bootstrap_checksum}" in output[0].get("output", ""):
        ctx.logger.log(
            f"Bootstrap already executed in container '{container_name}'. Skipping.",
            level=ctx.logger.verbose,
        )
        return False

    ctx.logger.log(
        f"Executing bootstrap script in container '{container_name}'...",
        level=ctx.logger.verbose,
    )
    ctx.cmd_executor.execute_commands(
        f"docker cp {bootstrap_file} {container_name}:/tmp/"
    )
    ctx.cmd_executor.execute_commands(
        f"/tmp/{os.path.basename(bootstrap_file)}",
        f'bash -c "echo {bootstrap_checksum} >> /opt/minipresto/bootstrap_status.txt"',
        container=container,
    )

    ctx.logger.log(
        f"Successfully executed bootstrap script in container '{container_name}'.",
        level=ctx.logger.verbose,
    )
    return True


@minipresto.cli.pass_environment
def handle_config_properties(ctx):
    """Checks for duplicates in the Presto config.properties file and logs
    warnings for any detected duplicates.
    """

    ctx.logger.log(
        "Checking Presto config.properties for duplicate properties...",
        level=ctx.logger.verbose,
    )
    container = ctx.docker_client.containers.get("presto")
    output = ctx.cmd_executor.execute_commands(
        f"cat {ETC_PRESTO}/config.properties",
        suppress_output=True,
        container=container,
    )

    config_props = output[0].get("output", "")
    if not config_props:
        raise err.MiniprestoError(
            "Presto config.properties file unable to be read from Presto container."
        )

    config_props = config_props.strip().split("\n")
    config_props.sort()

    duplicates = []
    for i, prop in enumerate(config_props):
        prop = prop.strip().split("=")
        try:
            next_prop = config_props[i + 1].strip().split("=")
        except:
            next_prop = [""]
        if prop[0].strip() == next_prop[0].strip():
            duplicates.extend(["".join(prop), "".join(next_prop)])
        elif duplicates:
            duplicates = set(duplicates)
            duplicates_string = "\n".join(duplicates)
            ctx.logger.log(
                f"Duplicate Presto configuration properties detected in "
                f"config.properties file:\n{duplicates_string}",
                level=ctx.logger.warn,
                split_lines=False,
            )
            duplicates = []


@minipresto.cli.pass_environment
def append_user_config(ctx, containers_to_restart=[]):
    """Appends Presto config from minipresto.cfg file if present and if it does
    not already exist in the Presto container. If anything is appended to the
    Presto config, the Presto container is added to the restart list if it's not
    already in the list.
    """

    user_presto_config = ctx.env.get_var("CONFIG", "")
    if user_presto_config:
        user_presto_config = user_presto_config.strip().split("\n")

    user_jvm_config = ctx.env.get_var("JVM_CONFIG", "")
    if user_jvm_config:
        user_jvm_config = user_jvm_config.strip().split("\n")

    if not user_presto_config and not user_jvm_config:
        return containers_to_restart

    ctx.logger.log(
        "Appending Presto config from minipresto.cfg to Presto config files...",
        level=ctx.logger.verbose,
    )

    presto_container = ctx.docker_client.containers.get("presto")
    if not presto_container:
        raise err.MiniprestoError(
            f"Attempting to append Presto configuration in Presto container, "
            f"but no running Presto container found."
        )

    current_configs = ctx.cmd_executor.execute_commands(
        f"cat {ETC_PRESTO}/config.properties",
        f"cat {ETC_PRESTO}/jvm.config",
        container=presto_container,
    )

    current_presto_config = current_configs[0].get("output", "")
    current_jvm_config = current_configs[1].get("output", "")

    def add_configs(configs, filename):
        for config in configs:
            if config not in current_presto_config:
                append_presto_config = (
                    f'bash -c "cat <<EOT >> {ETC_PRESTO}/{filename}\n{config}\nEOT"'
                )
                ctx.cmd_executor.execute_commands(
                    append_presto_config, container=presto_container
                )

    add_configs(user_presto_config, "config.properties")
    add_configs(user_jvm_config, "jvm.config")

    if not "presto" in containers_to_restart:
        containers_to_restart.append("presto")

    return containers_to_restart


@minipresto.cli.pass_environment
def restart_containers(ctx, containers_to_restart=[]):
    """Restarts all the containers in the list."""

    if containers_to_restart == []:
        return

    # Remove any duplicates
    containers_to_restart = list(set(containers_to_restart))

    for container in containers_to_restart:
        try:
            container = ctx.docker_client.containers.get(container)
            ctx.logger.log(
                f"Restarting container '{container.name}'...", level=ctx.logger.verbose
            )
            container.restart()
        except NotFound:
            raise err.MiniprestoError(
                f"Attempting to restart container '{container.name}', but the container was not found."
            )


@minipresto.cli.pass_environment
def initialize_containers(ctx):
    """Initializes each container with /opt/minipresto/bootstrap_status.txt."""

    containers = ctx.docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    for container in containers:
        output = ctx.cmd_executor.execute_commands(
            "cat /opt/minipresto/bootstrap_status.txt",
            suppress_output=True,
            container=container,
            trigger_error=False,
        )
        output_string = output[0].get("output", "").strip()
        if "no such file or directory" in output_string.lower():
            ctx.cmd_executor.execute_commands(
                "mkdir -p /opt/minipresto/",
                "touch /opt/minipresto/bootstrap_status.txt",
                container=container,
            )
        elif output[0].get("return_code", None) == 0:
            continue
        else:
            raise err.MiniprestoError(
                f"Command failed.\n"
                f"Output: {output_string}\n"
                f"Exit code: {output[0].get('return_code', None)}"
            )


@minipresto.cli.pass_environment
def rollback_provision(ctx, no_rollback):
    """Rolls back the provisioning command in the event of an error."""

    if no_rollback:
        ctx.logger.log(
            f"Errors occurred during environment provisioning and rollback has been disabled. "
            f"Provisioned resources will remain in an unaltered state.",
            level=ctx.logger.warn,
        )
        return
    ctx.logger.log(
        f"Rolling back provisioned resources due to "
        f"errors encountered while provisioning the environment.",
        level=ctx.logger.warn,
    )

    containers = ctx.docker_client.containers.list(
        filters={"label": RESOURCE_LABEL}, all=True
    )

    for container in containers:
        container.stop()
        container.remove()
