#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# Instead of using the Docker SDK, this script will form a Docker Compose
# command string to execute straight through the docker compose CLI. This is
# required because the Docker SDK does not support communication with Compose
# files, and Minitrino benefits hugely from Docker Compose.

import os
import re
import stat
import hashlib
import time
import click
import yaml

from minitrino.cli import pass_environment
from minitrino import utils
from minitrino import errors as err
from minitrino.settings import RESOURCE_LABEL
from minitrino.settings import ETC_TRINO
from minitrino.settings import LIC_VOLUME_MOUNT
from minitrino.settings import LIC_MOUNT_PATH
from minitrino.settings import DUMMY_LIC_MOUNT_PATH
from minitrino.settings import TRINO_CONFIG
from minitrino.settings import TRINO_JVM_CONFIG
from minitrino.settings import WORKER_CONFIG_PROPS

from docker.errors import NotFound
from concurrent.futures import ThreadPoolExecutor, as_completed


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
    "-w",
    "--workers",
    "workers",
    default=0,
    type=int,
    help=("""The number of workers to provision (default: 0)."""),
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
        """Appends native docker compose commands to the generated
        docker compose shell command. Run `docker compose up --help` to see all
        available options.

        Example: minitrino provision --docker-native --build

        Example: minitrino provision --docker-native '--remove-orphans
        --force-recreate'"""
    ),
)
@utils.exception_handler
@pass_environment
def cli(ctx, modules, workers, no_rollback, docker_native):
    """Provision command for Minitrino. If the resulting docker compose command
    is unsuccessful, the function exits with a non-zero status code."""

    utils.check_daemon(ctx.docker_client)
    utils.check_lib(ctx)
    utils.check_starburst_ver(ctx)
    modules = list(modules)
    modules = append_running_modules(modules)
    modules = utils.check_dependent_modules(ctx, modules)
    check_compatibility(modules)
    check_enterprise(modules)
    check_volumes(modules)

    if not modules:
        ctx.logger.info(
            f"No modules specified. Provisioning standalone Trino cluster..."
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
        compose_cmd = build_command(docker_native, cmd_chunk)

        ctx.cmd_executor.execute_commands(compose_cmd, environment=ctx.env)
        initialize_containers()

        c_restart = execute_bootstraps(modules)
        c_restart = write_trino_cfg(c_restart, modules)
        check_dup_cfgs()
        c_restart = provision_workers(c_restart, workers)
        restart_containers(c_restart)
        ctx.logger.info(f"Environment provisioning complete.")

    except Exception as e:
        rollback(no_rollback)
        utils.handle_exception(e)


@pass_environment
def append_running_modules(ctx, modules=[]):
    """Checks if any modules are already running. If they are, they are appended
    to the provided modules list and the updated list is returned."""

    ctx.logger.verbose("Checking for running modules...")
    running_modules = ctx.modules.get_running_modules()

    if running_modules:
        ctx.logger.verbose(
            f"Identified the following running modules: {running_modules}. "
            f"Appending the running module list to the list of modules to provision.",
        )

    modules = list(modules)
    modules.extend(running_modules)
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
    If they are, we check that a pointer to a SEP license is provided."""

    ctx.logger.verbose(
        "Checking for SEP license for enterprise modules...",
    )

    yaml_path = os.path.join(ctx.minitrino_lib_dir, "docker-compose.yml")
    with open(yaml_path) as f:
        yaml_file = yaml.load(f, Loader=yaml.FullLoader)
    volumes = yaml_file.get("services", {}).get("trino", {}).get("volumes", [])

    if LIC_VOLUME_MOUNT not in volumes:
        raise err.UserError(
            f"The required license volume in the library's root docker-compose.yml "
            f"is either commented out or deleted: {yaml_path}. For reference, "
            f"the proper volume mount is: '{LIC_VOLUME_MOUNT}'"
        )

    enterprise_modules = []
    for module in modules:
        if ctx.modules.data.get(module, {}).get("enterprise", False):
            enterprise_modules.append(module)

    if enterprise_modules:
        if not ctx.env.get("LIC_PATH", False):
            raise err.UserError(
                f"Module(s) {enterprise_modules} requires a Starburst license. "
                f"You must provide a path to a Starburst license via the "
                f"LIC_PATH environment variable"
            )
        ctx.env.update({"LIC_MOUNT_PATH": LIC_MOUNT_PATH})
    elif ctx.env.get("LIC_PATH", False):
        ctx.env.update({"LIC_MOUNT_PATH": LIC_MOUNT_PATH})
    else:
        ctx.env.update({"LIC_PATH": "./modules/resources/dummy.license"})
        ctx.env.update({"LIC_MOUNT_PATH": DUMMY_LIC_MOUNT_PATH})


@pass_environment
def check_volumes(ctx, modules=[]):
    """Checks if any of the modules have persistent volumes and issues a warning
    to the user if so."""

    ctx.logger.verbose(
        "Checking modules for persistent volumes...",
    )

    for module in modules:
        if ctx.modules.data.get(module, {}).get("yaml_dict", {}).get("volumes", {}):
            ctx.logger.warn(
                f"Module '{module}' has persistent volumes associated with it. "
                f"To delete these volumes, remember to run `minitrino remove --volumes`.",
            )


@pass_environment
def chunk(ctx, modules=[]):
    """Builds docker compose command chunk for the chosen modules. Returns a
    command chunk string."""

    chunk = []
    for module in modules:
        yaml_file = ctx.modules.data.get(module, {}).get("yaml_file", "")
        chunk.extend(f"-f {yaml_file} \\\n")
    return "".join(chunk)


@pass_environment
def build_command(ctx, docker_native="", chunk=""):
    """Builds a formatted docker compose command for shell execution. Returns a
    docker compose command string."""

    cmd = []
    compose_env_string = ""
    for k, v in ctx.env.items():
        compose_env_string += f'{k.upper()}="{v}" '

    cmd.extend(
        [
            compose_env_string,
            "\\\n",
            "docker compose -f ",
            os.path.join(ctx.minitrino_lib_dir, "docker-compose.yml"),
            " \\\n",
            chunk,  # Module YAML paths
            "up -d",
        ]
    )

    if docker_native:
        ctx.logger.verbose(
            f"Received native Docker Compose options: '{docker_native}'",
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
    `/opt/minitrino/bootstrap-status.txt` file has the same checksum as the
    bootstrap script that is about to be executed, the boostrap script is
    skipped.

    Returns `False` if the script is not executed and `True` if it is."""

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

    checksum = hashlib.md5(open(bootstrap_file, "rb").read()).hexdigest()
    container = ctx.docker_client.containers.get(container_name)

    # Check if this script has already been executed
    output = ctx.cmd_executor.execute_commands(
        "cat /opt/minitrino/bootstrap-status.txt",
        container=container,
        trigger_error=False,
    )

    if f"{checksum}" in output[0].get("output", ""):
        ctx.logger.verbose(
            f"Bootstrap already executed in container '{container_name}'. Skipping.",
        )
        return False

    ctx.logger.verbose(
        f"Executing bootstrap script in container '{container_name}'...",
    )

    ctx.cmd_executor.execute_commands(
        f"docker cp {bootstrap_file} {container_name}:/tmp/"
    )

    # Record executed file checksum
    ctx.cmd_executor.execute_commands(
        f"/tmp/{os.path.basename(bootstrap_file)}",
        f'bash -c "echo {checksum} >> /opt/minitrino/bootstrap-status.txt"',
        container=container,
    )

    ctx.logger.verbose(
        f"Successfully executed bootstrap script in container '{container_name}'.",
    )

    return True


def split_cfg(cfgs=""):
    cfgs = cfgs.strip().split("\n")
    for i, cfg in enumerate(cfgs):
        cfg = re.sub(r"\s*=\s*", "=", cfg)
        cfgs[i] = cfg.split("=", 1)
    return cfgs


@pass_environment
def get_current_trino_cfgs(ctx):
    """Get Trino config.properties and jvm.config files. Return the two sets of
    configs as lists, e.g.:

    [['a', 'b'], ['c', 'd'], ['e', 'f']]
    """

    current_cfgs = ctx.cmd_executor.execute_commands(
        f"cat {ETC_TRINO}/{TRINO_CONFIG}",
        f"cat {ETC_TRINO}/{TRINO_JVM_CONFIG}",
        container=ctx.docker_client.containers.get("trino"),
        suppress_output=True,
    )

    current_trino_cfgs = split_cfg(current_cfgs[0].get("output", ""))
    current_jvm_cfg = split_cfg(current_cfgs[1].get("output", ""))

    return current_trino_cfgs, current_jvm_cfg


@pass_environment
def write_trino_cfg(ctx, c_restart=[], modules=[]):
    """Appends Trino config from various modules if specified in the module YAML
    file. The Trino container is added to the restart list if any configs are
    written to files in the container."""

    def handle_password_authenticators(cfgs):
        merge = []
        for i, cfg in enumerate(cfgs):
            if cfg[0] == "http-server.authentication.type":
                merge.append(i)

        if not merge:
            return cfgs

        auth_property = "http-server.authentication.type="
        for i, cfg in enumerate(merge):
            if i + 1 == len(merge):
                auth_property += cfgs[cfg][1].upper()
            else:
                auth_property += f"{cfgs[cfg][1].upper()},"

        cfgs = [x for i, x in enumerate(cfgs) if i not in merge]
        cfgs.append(auth_property.split("="))
        return cfgs

    trino_container = ctx.docker_client.containers.get("trino")

    if not trino_container:
        raise err.MinitrinoError(
            f"Attempting to append Trino configuration in Trino container, "
            f"but no running Trino container was found."
        )

    cfgs = []
    jvm_cfg = []
    modules.append("trino")  # check if user placed configs in root compose yaml

    for module in modules:
        if module == "trino":
            with open(os.path.join(ctx.minitrino_lib_dir, "docker-compose.yml")) as f:
                yaml_file = yaml.load(f, Loader=yaml.FullLoader)
        else:
            yaml_file = ctx.modules.data.get(module, {}).get("yaml_dict")
        usr_cfgs = (
            yaml_file.get("services", {})
            .get("trino", {})
            .get("environment", {})
            .get("CONFIG_PROPERTIES", [])
        )
        user_jvm_cfg = (
            yaml_file.get("services", {})
            .get("trino", {})
            .get("environment", {})
            .get("JVM_CONFIG", [])
        )

        if usr_cfgs:
            cfgs.extend(split_cfg(usr_cfgs))
        if user_jvm_cfg:
            jvm_cfg.extend(split_cfg(user_jvm_cfg))

    if not cfgs and not jvm_cfg:
        return c_restart

    cfgs = handle_password_authenticators(cfgs)

    checksum_file = "/opt/minitrino/user-config.txt"
    checksum_data = bytes(str([cfgs, jvm_cfg]), "utf-8")
    checksum = hashlib.md5(checksum_data).hexdigest()

    output = ctx.cmd_executor.execute_commands(
        f"cat {checksum_file}",
        container=trino_container,
        trigger_error=False,
    )

    old_checksum = output[0].get("output", "").strip().lower()
    if not "no such file or directory" in old_checksum:
        if old_checksum == checksum:
            ctx.logger.verbose(
                "User-defined config already added to config files. Skipping...",
            )
            return c_restart

    ctx.logger.verbose(
        "Checking Trino server status before updating configs...",
    )

    retry = 0
    while retry <= 30:
        logs = trino_container.logs().decode()
        if "======== SERVER STARTED ========" in logs:
            ctx.logger.verbose(
                "Trino server started.",
            )
            break
        elif trino_container.status != "running":
            raise err.MinitrinoError(
                f"Trino container stopped running. Inspect the container logs if the "
                f"container is still available. If the container was rolled back, rerun "
                f"the command with the '--no-rollback' option, then inspect the logs."
            )
        else:
            ctx.logger.verbose(
                "Waiting for Trino server to start...",
            )
            time.sleep(1)
            retry += 1

    def append_cfgs(trino_container, usr_cfgs, current_cfgs, filename):
        """If there is an overlapping config key, replace it with the user
        config."""

        if not usr_cfgs:
            return

        current_cfgs = [
            cfg
            for cfg in current_cfgs
            if not any(cfg[0] == usr_cfg[0] for usr_cfg in usr_cfgs)
        ]

        current_cfgs.extend(usr_cfgs)
        current_cfgs = ["=".join(x) for x in current_cfgs]

        ctx.logger.verbose(
            f"Removing existing {filename} file...",
        )
        ctx.cmd_executor.execute_commands(
            f"rm {ETC_TRINO}/{filename}", container=trino_container
        )

        ctx.logger.verbose(
            f"Writing new config to {filename}...",
        )
        for current_cfg in current_cfgs:
            append_cfg = (
                f'bash -c "cat <<EOT >> {ETC_TRINO}/{filename}\n{current_cfg}\nEOT"'
            )
            ctx.cmd_executor.execute_commands(
                append_cfg, container=trino_container, suppress_output=True
            )

    ctx.logger.verbose(
        "Appending user-defined Trino config to Trino container config...",
    )

    current_trino_cfgs, current_jvm_cfg = get_current_trino_cfgs()
    append_cfgs(trino_container, cfgs, current_trino_cfgs, TRINO_CONFIG)
    append_cfgs(trino_container, jvm_cfg, current_jvm_cfg, TRINO_JVM_CONFIG)

    if not "trino" in c_restart:
        c_restart.append("trino")

    ctx.logger.verbose("Recording config checksum...")
    output = ctx.cmd_executor.execute_commands(
        f'bash -c "echo {checksum} > {checksum_file}"', container=trino_container
    )

    return c_restart


@pass_environment
def check_dup_cfgs(ctx):
    """Checks for duplicate configs in Trino config files (jvm.config and
    config.properties). This is a safety check for modules that may improperly
    modify these files."""

    def log_duplicates(cfgs, filename):
        ctx.logger.verbose(
            f"Checking Trino '{filename}' file for duplicate configs...",
        )

        unique = {}
        for cfg in cfgs:
            key = cfg[0]
            if key in unique:
                unique[key].append(cfg)
            else:
                unique[key] = [cfg]

        duplicates = ["=".join(x) for y in unique.values() for x in y if len(y) > 1]

        if duplicates:
            ctx.logger.warn(
                f"Duplicate Trino configuration properties detected in "
                f"'{filename}' file:\n{str(duplicates)}",
            )

    current_trino_cfgs, current_jvm_cfg = get_current_trino_cfgs()

    log_duplicates(current_trino_cfgs, TRINO_CONFIG)
    log_duplicates(current_jvm_cfg, TRINO_JVM_CONFIG)


@pass_environment
def restart_containers(ctx, c_restart=[]):
    """Restarts all the containers in the list."""

    if c_restart == []:
        return

    c_restart = list(set(c_restart))

    def restart_container(container_name):
        """Helper function to restart a single container."""
        try:
            container = ctx.docker_client.containers.get(container_name)
            ctx.logger.verbose(f"Restarting container '{container.name}'...")
            container.restart()
            ctx.logger.verbose(f"Container '{container.name}' restarted successfully.")
        except NotFound:
            raise err.MinitrinoError(
                f"Attempting to restart container '{container_name}', but the container was not found."
            )

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(restart_container, container): container
            for container in c_restart
        }

        for future in as_completed(futures):
            container_name = futures[future]
            try:
                future.result()
            except err.MinitrinoError as e:
                ctx.logger.error(
                    f"Error while restarting container '{container_name}': {str(e)}"
                )

    ctx.logger.info("All specified containers have been restarted.")


@pass_environment
def initialize_containers(ctx):
    """Initializes each container with /opt/minitrino/ directory."""

    containers = ctx.docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    for container in containers:
        output = ctx.cmd_executor.execute_commands(
            "mkdir -p /opt/minitrino/",
            container=container,
            trigger_error=False,
        )
        if output[0].get("return_code", None) in [0, 126]:
            continue
        else:
            raise err.MinitrinoError(
                f"Command failed.\n"
                f"Output: {output[0].get('output', '').strip()}\n"
                f"Exit code: {output[0].get('return_code', None)}"
            )


@pass_environment
def provision_workers(ctx, c_restart=[], workers=0):
    """Provisions (or updates) workers.

    Scenarios:

    1. No workers are specified and no workers are running: do nothing.
    2. The user specifies a worker count and no workers exist: the specified
       number of workers are provisioned.
    3. The user does not specify a worker count, but there are active workers:
       the worker count will be set to the number of running workers.
    4. The user specifies a worker count greater than the number of active
       workers: the worker count will increase to the specified number.
    5. The user specifies a worker count less than the number of active workers:
       the worker with the highest iterator is removed from the network.

    I am enumerating all cases for my own sanity.
    """

    # Check for running worker containers
    containers = ctx.docker_client.containers.list()
    worker_containers = [
        c.name
        for c in containers
        if c.name.startswith("trino-worker-")
        and c.labels.get("com.starburst.tests") == "minitrino"
    ]

    # Scenario 1
    if workers == 0 and len(worker_containers) == 0:
        return c_restart
    # Scenario 2
    if workers > len(worker_containers):
        pass
    # Scenario 3
    if workers == 0 and len(worker_containers) > 0:
        workers = len(worker_containers)
    # Scenario 4
    if workers > len(worker_containers):
        pass
    # Scenario 5
    if workers < len(worker_containers):
        worker_containers.sort(reverse=True)
        excess = len(worker_containers) - workers
        remove = worker_containers[:excess]
        for c in remove:
            c = ctx.docker_client.containers.get(c)
            c.kill()
            c.remove()
            identifier = utils.generate_identifier({"ID": c.short_id, "Name": c.name})
            ctx.logger.warn(f"Removed excess worker: {identifier}")

    worker_img = f"minitrino/trino:{ctx.env.get('STARBURST_VER')}"
    network_name = "minitrino_default"

    coordinator = ctx.docker_client.containers.get("trino")

    for i in range(1, workers + 1):
        worker_name = f"trino-worker-{i}"
        try:
            worker = ctx.docker_client.containers.get(worker_name)
        except NotFound:
            worker = ctx.docker_client.containers.run(
                worker_img,
                name=worker_name,
                detach=True,
                network=network_name,
                labels={
                    "com.starburst.tests": "minitrino",
                    "com.starburst.tests.module": "trino",
                    "com.docker.compose.service": worker_name,  # OrbStack dashboard doesn't display the container name correctly w/out this
                },
            )
            ctx.logger.verbose(
                f"Created and started worker container: '{worker_name}' in network '{network_name}'"
            )

        # Copy the source directory from the coordinator to the worker container
        tar_path = "/tmp/starburst.tar.gz"
        ctx.cmd_executor.execute_commands(
            f"tar czf {tar_path} -C /etc starburst",
            container=coordinator,
            docker_user="starburst",
        )

        # Copy the tar file from the coordinator container
        bits, _ = coordinator.get_archive(tar_path)
        tar_stream = b"".join(bits)

        # Put the tar file into the new worker container & extract
        worker.put_archive("/tmp", tar_stream)
        ctx.cmd_executor.execute_commands(
            f"tar xzf /tmp/starburst.tar.gz -C /etc",
            container=worker,
            docker_user="starburst",
        )

        # Overwrite worker config.properties
        ctx.cmd_executor.execute_commands(
            f"bash -c \"echo '{WORKER_CONFIG_PROPS}' > {ETC_TRINO}/{TRINO_CONFIG}\"",
            container=worker,
            docker_user="starburst",
        )

        c_restart.append(worker_name)
        ctx.logger.verbose(f"Copied {ETC_TRINO} to '{worker_name}'")

    return c_restart


@pass_environment
def rollback(ctx, no_rollback):
    """Rolls back the provisioning command in the event of an error."""

    if no_rollback:
        ctx.logger.warn(
            f"Errors occurred during environment provisioning and rollback has been disabled. "
            f"Provisioned resources will remain in an unaltered state.",
        )
        return

    ctx.logger.warn(
        f"Rolling back provisioned resources due to "
        f"errors encountered while provisioning the environment.",
    )

    containers = ctx.docker_client.containers.list(
        filters={"label": RESOURCE_LABEL}, all=True
    )

    for container in containers:
        container.kill()
        container.remove()
