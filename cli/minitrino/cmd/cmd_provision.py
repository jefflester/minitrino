#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# Instead of using the Docker SDK, this script will form a Docker Compose
# command string to execute straight through the docker-compose CLI. This is
# required because the Docker SDK does not support communication with Compose
# files, and Minitrino benefits hugely from Docker Compose.

import os
import stat
import hashlib
import time
import click
import yaml

from minitrino.cli import pass_environment
from minitrino import utils
from minitrino import errors as err
from minitrino.settings import RESOURCE_LABEL
from minitrino.settings import MODULE_ROOT
from minitrino.settings import MODULE_CATALOG
from minitrino.settings import MODULE_SECURITY
from minitrino.settings import ETC_TRINO
from minitrino.settings import TRINO_CONFIG
from minitrino.settings import TRINO_JVM_CONFIG

from docker.errors import NotFound


@click.command(
    "provision",
    help=(
        """Provision an environment based on specified modules. All options are
        optional and can be left empty."""
    ),
)
@click.option(
    "-m",
    "--module",
    "modules",
    default=[],
    type=str,
    multiple=True,
    help=("""A specific module to provision."""),
)
@click.option(
    "-n",
    "--no-rollback",
    is_flag=True,
    default=False,
    help=(
        """Do not rollback provisioned resources in the event of an
        error."""
    ),
)
@click.option(
    "-d",
    "--docker-native",
    default="",
    type=str,
    help=(
        """Appends native docker-compose commands to the generated
        docker-compose shell command. Run `docker-compose up --help` to see all
        available options.

        Example: minitrino provision --docker-native --build

        Example: minitrino provision --docker-native '--remove-orphans
        --force-recreate'"""
    ),
)
@utils.exception_handler
@pass_environment
def cli(ctx, modules, no_rollback, docker_native):
    """Provision command for Minitrino. If the resulting docker-compose command
    is unsuccessful, the function exits with a non-zero status code."""

    utils.check_daemon(ctx.docker_client)
    utils.check_lib(ctx)
    modules = append_running_modules(modules)
    check_compatibility(modules)
    check_enterprise(modules)

    if not modules:
        ctx.logger.log(
            f"No catalog or security options received. Provisioning "
            f"standalone Trino container..."
        )
    else:
        for module in modules:
            if not ctx.modules.data.get(module, False):
                raise err.UserError(
                    f"Invalid module: '{module}'. It was not found "
                    f"in the Minitrino library at {ctx.minitrino_lib_dir}"
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
        check_dup_configs()
        restart_containers(containers_to_restart)
        ctx.logger.log(f"Environment provisioning complete.")

    except Exception as e:
        rollback_provision(no_rollback)
        utils.handle_exception(e)


@pass_environment
def append_running_modules(ctx, modules=[]):
    """Checks if any modules are already running. If they are, they are appended
    to the provided modules list and the updated list is returned."""

    ctx.logger.log("Checking for running modules...", level=ctx.logger.verbose)
    running_modules_dict = ctx.modules.get_running_modules()
    running_modules_list = []

    for module in running_modules_dict:
        running_modules_list.append(module)

    if running_modules_list:
        ctx.logger.log(
            f"Identified the following running modules: {running_modules_list}. "
            f"Appending the running module list to the list of modules to provsion.",
            level=ctx.logger.verbose,
        )

    modules = list(modules)
    modules.extend(running_modules_list)
    return list(set(modules))


@pass_environment
def check_compatibility(ctx, modules=[]):
    """Checks if any of the provided modules are mutually exclusive of each
    other. If they are, a user error is raised."""

    for module in modules:
        incompatible = ctx.modules.data.get(module, {}).get("incompatibleModules", [])
        if not incompatible:
            continue
        for module_inner in modules:
            if (module_inner in incompatible) or (
                incompatible[0] == "*" and len(modules) > 1
            ):
                raise err.UserError(
                    f"Incompatible modules detected. Tried to provision module "
                    f"'{module_inner}', but found that the module is incompatible "
                    f"with module '{module}'. Incompatible modules listed for module "
                    f"'{module}' are: {incompatible}",
                    f"You can see which modules are incompatible with this module by "
                    f"running 'minitrino modules -m {module}'",
                )


@pass_environment
def check_enterprise(ctx, modules=[]):
    """Checks if any of the provided modules are Starburst Enterprise features.
    If they are, we check that a pointer to an SEP license is provided."""

    ctx.logger.log(
        "Checking for SEP license for enterprise modules...",
        level=ctx.logger.verbose,
    )

    for module in modules:
        enterprise = ctx.modules.data.get(module, {}).get("enterprise", False)
        if enterprise:
            yaml_path = os.path.join(ctx.minitrino_lib_dir, "docker-compose.yml")
            with open(yaml_path) as f:
                yaml_file = yaml.load(f, Loader=yaml.FullLoader)
            if (
                not yaml_file.get("services", False)
                .get("trino", False)
                .get("volumes", False)
            ):
                raise err.UserError(
                    f"Module {module} requires a Starburst license. "
                    f"The license volume in the library's docker-compose.yml "
                    f"file must be uncommented at: {yaml_path}"
                )
            if not ctx.env.get_var("STARBURST_LIC_PATH", False):
                raise err.UserError(
                    f"Module {module} requires a Starburst license. "
                    f"You must provide a path to a Starburst license via the "
                    f"STARBURST_LIC_PATH environment variable"
                )


@pass_environment
def chunk(ctx, modules=[]):
    """Builds docker-compose command chunk for the chosen modules. Returns a
    command chunk string."""

    chunk = []
    for mod in modules:
        yaml_file = ctx.modules.data.get(mod, "").get("yaml_file", "")
        chunk.extend(f"-f {yaml_file} \\\n")
    return "".join(chunk)


@pass_environment
def build_command(ctx, docker_native="", compose_env={}, chunk=""):
    """Builds a formatted docker-compose command for shell execution. Returns a
    docker-compose command string."""

    cmd = []
    compose_env_string = ""
    for k, v in compose_env.items():
        compose_env_string += f'{k.upper()}="{v}" '

    cmd.extend(
        [
            compose_env_string,
            "\\\n",
            "docker-compose -f ",
            os.path.join(ctx.minitrino_lib_dir, "docker-compose.yml"),
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


@pass_environment
def execute_bootstraps(ctx, modules=[]):
    """Executes bootstrap script for each container that has one––bootstrap
    scripts will only execute once the container is fully running to prevent
    conflicts with procedures executing as part of the container's entrypoint.
    After each script executes, the relevant container is added to a restart
    list.

    Returns a list of containers names which had bootstrap scripts executed
    inside of them."""

    services = []
    for module in modules:
        yaml_file = ctx.modules.data.get(module, {}).get("yaml_file", "")
        module_services = (
            ctx.modules.data.get(module, {}).get("yaml_dict", {}).get("services", {})
        )
        if not module_services:
            raise err.MinitrinoError(
                f"Invalid Docker Compose YAML file (no 'services' section found): {yaml_file}"
            )
        # Get all services defined in YAML file
        for service_key, service_dict in module_services.items():
            services.append([service_key, service_dict, yaml_file])

    containers = []
    # Get all container names for each service
    for service in services:
        bootstrap = service[1].get("environment", {}).get("MINITRINO_BOOTSTRAP")
        if bootstrap is None:
            continue
        container_name = service[1].get("container_name")
        if container_name is None:
            # If there is not container name, the service name becomes the name
            # of the container
            container_name = service[0]
        if execute_container_bootstrap(bootstrap, container_name, service[2]):
            containers.append(container_name)
    return containers


@pass_environment
def execute_container_bootstrap(ctx, bootstrap="", container_name="", yaml_file=""):
    """Executes a single bootstrap inside a container. If the
    `/opt/minitrino/bootstrap_status.txt` file has the same checksum as the
    bootstrap script that is about to be executed, the boostrap script is
    skipped.

    Returns `False` if the script is not executed and `True` if it is."""

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

    # Check if this script has already been executed
    output = ctx.cmd_executor.execute_commands(
        "cat /opt/minitrino/bootstrap_status.txt",
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

    # Record executed file checksum
    ctx.cmd_executor.execute_commands(
        f"/tmp/{os.path.basename(bootstrap_file)}",
        f'bash -c "echo {bootstrap_checksum} >> /opt/minitrino/bootstrap_status.txt"',
        container=container,
    )

    ctx.logger.log(
        f"Successfully executed bootstrap script in container '{container_name}'.",
        level=ctx.logger.verbose,
    )

    return True


@pass_environment
def check_dup_configs(ctx):
    """Checks for duplicate configs in Trino config files (jvm.config and
    config.properties). This is a safety check for modules that may improperly
    modify these files.

    Duplicates will only be registered for JVM config if the configs are
    identical. For config.properties, duplicates will be registered if there are
    multiple overlapping property keys."""

    check_files = [TRINO_CONFIG, TRINO_JVM_CONFIG]
    for check_file in check_files:
        ctx.logger.log(
            f"Checking Trino {check_file} for duplicate configs...",
            level=ctx.logger.verbose,
        )
        container = ctx.docker_client.containers.get("trino")
        output = ctx.cmd_executor.execute_commands(
            f"cat {ETC_TRINO}/{check_file}",
            suppress_output=True,
            container=container,
        )

        configs = output[0].get("output", "")
        if not configs:
            raise err.MinitrinoError(
                f"Trino {check_file} file unable to be read from Trino container."
            )

        configs = configs.strip().split("\n")
        configs.sort()

        duplicates = []
        if check_file == TRINO_CONFIG:
            for i, config in enumerate(configs):
                if config.startswith("#"):
                    continue
                config = utils.parse_key_value_pair(config, err_type=err.UserError)
                if config is None:
                    continue
                if i + 1 != len(configs):
                    next_config = utils.parse_key_value_pair(
                        configs[i + 1], err_type=err.UserError
                    )
                    if config[0] == next_config[0]:
                        duplicates.extend(["=".join(config), "=".join(next_config)])
                else:
                    next_config = [""]
                if config[0] == next_config[0]:
                    duplicates.extend(["=".join(config), "=".join(next_config)])
                elif duplicates:
                    duplicates = set(duplicates)
                    duplicates_string = "\n".join(duplicates)
                    ctx.logger.log(
                        f"Duplicate Trino configuration properties detected in "
                        f"{check_file} file:\n{duplicates_string}",
                        level=ctx.logger.warn,
                    )
                    duplicates = []
        else:  # JVM config
            for i, config in enumerate(configs):
                config = config.strip()
                if config.startswith("#") or not config:
                    continue
                if i + 1 != len(configs):
                    next_config = configs[i + 1].strip()
                else:
                    next_config = ""
                if config == next_config:
                    duplicates.extend([config, next_config])
                elif duplicates:
                    duplicates_string = "\n".join(duplicates)
                    ctx.logger.log(
                        f"Duplicate Trino configuration properties detected in "
                        f"{check_file} file:\n{duplicates_string}",
                        level=ctx.logger.warn,
                    )
                    duplicates = []


@pass_environment
def append_user_config(ctx, containers_to_restart=[]):
    """Appends Trino config from minitrino.cfg file. If the config is not
    present, it is added. If it exists, it is replaced. If anything changes in
    the Trino config, the Trino container is added to the restart list if it's
    not already in the list."""

    user_trino_config = ctx.env.get_var("CONFIG", "")
    if user_trino_config:
        user_trino_config = user_trino_config.strip().split("\n")

    user_jvm_config = ctx.env.get_var("JVM_CONFIG", "")
    if user_jvm_config:
        user_jvm_config = user_jvm_config.strip().split("\n")

    if not user_trino_config and not user_jvm_config:
        return containers_to_restart

    ctx.logger.log(
        "Appending user-defined Trino config to Trino container config...",
        level=ctx.logger.verbose,
    )

    trino_container = ctx.docker_client.containers.get("trino")
    if not trino_container:
        raise err.MinitrinoError(
            f"Attempting to append Trino configuration in Trino container, "
            f"but no running Trino container was found."
        )

    ctx.logger.log(
        "Checking Trino server status before updating configs...",
        level=ctx.logger.verbose,
    )
    retry = 0
    while retry <= 30:
        logs = trino_container.logs().decode()
        if "======== SERVER STARTED ========" in logs:
            break
        elif trino_container.status != "running":
            raise err.MinitrinoError(
                f"Trino container stopped running. Inspect the container logs if the "
                f"container is still available. If the container was rolled back, rerun "
                f"the command with the '--no-rollback' option, then inspect the logs."
            )
        else:
            ctx.logger.log(
                "Trino server has not started. Waiting one second and trying again...",
                level=ctx.logger.verbose,
            )
            time.sleep(1)
            retry += 1

    current_configs = ctx.cmd_executor.execute_commands(
        f"cat {ETC_TRINO}/{TRINO_CONFIG}",
        f"cat {ETC_TRINO}/{TRINO_JVM_CONFIG}",
        container=trino_container,
        suppress_output=True,
    )

    current_trino_config = current_configs[0].get("output", "").strip().split("\n")
    current_jvm_config = current_configs[1].get("output", "").strip().split("\n")

    def append_configs(user_configs, current_configs, filename):

        # If there is an overlapping config key, replace it with the user
        # config. If there is not overlapping config key, append it to the
        # current config list.

        if filename == TRINO_CONFIG:
            for user_config in user_configs:
                user_config = utils.parse_key_value_pair(
                    user_config, err_type=err.UserError
                )
                if user_config is None:
                    continue
                for i, current_config in enumerate(current_configs):
                    if current_config.startswith("#"):
                        continue
                    current_config = utils.parse_key_value_pair(
                        current_config, err_type=err.UserError
                    )
                    if current_config is None:
                        continue
                    if user_config[0] == current_config[0]:
                        current_configs[i] = "=".join(user_config)
                        break
                    if (
                        i + 1 == len(current_configs)
                        and not "=".join(user_config) in current_configs
                    ):
                        current_configs.append("=".join(user_config))
        else:
            for user_config in user_configs:
                user_config = user_config.strip()
                if not user_config:
                    continue
                for i, current_config in enumerate(current_configs):
                    if current_config.startswith("#"):
                        continue
                    current_config = current_config.strip()
                    if not current_config:
                        continue
                    if user_config == current_config:
                        current_configs[i] = user_config
                        break
                    if (
                        i + 1 == len(current_configs)
                        and not user_config in current_configs
                    ):
                        current_configs.append(user_config)

        # Replace existing file with new values
        ctx.cmd_executor.execute_commands(
            f"rm {ETC_TRINO}/{filename}", container=trino_container
        )

        for current_config in current_configs:
            append_config = (
                f'bash -c "cat <<EOT >> {ETC_TRINO}/{filename}\n{current_config}\nEOT"'
            )
            ctx.cmd_executor.execute_commands(append_config, container=trino_container)

    append_configs(user_trino_config, current_trino_config, TRINO_CONFIG)
    append_configs(user_jvm_config, current_jvm_config, TRINO_JVM_CONFIG)

    if not "trino" in containers_to_restart:
        containers_to_restart.append("trino")

    return containers_to_restart


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
            ctx.logger.log(
                f"Restarting container '{container.name}'...", level=ctx.logger.verbose
            )
            container.restart()
        except NotFound:
            raise err.MinitrinoError(
                f"Attempting to restart container '{container.name}', but the container was not found."
            )


@pass_environment
def initialize_containers(ctx):
    """Initializes each container with /opt/minitrino/bootstrap_status.txt."""

    containers = ctx.docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    for container in containers:
        output = ctx.cmd_executor.execute_commands(
            "cat /opt/minitrino/bootstrap_status.txt",
            suppress_output=True,
            container=container,
            trigger_error=False,
        )
        output_string = output[0].get("output", "").strip()
        if "no such file or directory" in output_string.lower():
            ctx.cmd_executor.execute_commands(
                "mkdir -p /opt/minitrino/",
                "touch /opt/minitrino/bootstrap_status.txt",
                container=container,
            )
        elif output[0].get("return_code", None) == 0:
            continue
        else:
            raise err.MinitrinoError(
                f"Command failed.\n"
                f"Output: {output_string}\n"
                f"Exit code: {output[0].get('return_code', None)}"
            )


@pass_environment
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
