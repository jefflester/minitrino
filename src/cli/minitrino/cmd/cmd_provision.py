#!/usr/bin/env python3

import os
import re
import stat
import time
import socket
import click
import yaml

from minitrino.components import Environment
from minitrino.cli import pass_environment
from minitrino import utils
from minitrino import errors as err
from minitrino.settings import RESOURCE_LABEL
from minitrino.settings import ETC_DIR
from minitrino.settings import LIC_VOLUME_MOUNT
from minitrino.settings import LIC_MOUNT_PATH
from minitrino.settings import DUMMY_LIC_MOUNT_PATH
from minitrino.settings import CLUSTER_CONFIG
from minitrino.settings import CLUSTER_JVM_CONFIG
from minitrino.settings import WORKER_CONFIG_PROPS
from minitrino.settings import MIN_CLUSTER_VER
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
    "-i",
    "--image",
    default="",
    type=str,
    help=("""The cluster image type (trino or starburst). Defaults to trino."""),
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
def cli(ctx: Environment, modules, image, workers, no_rollback, docker_native):
    """Provision command for Minitrino. If the resulting docker compose command
    is unsuccessful, the function exits with a non-zero status code."""

    # An asterisk is invalid in this context
    if ctx.cluster_name == "*":
        raise err.UserError(
            f"Invalid cluster name: '{ctx.cluster_name}'. Please specify a valid "
            f"cluster name containing only alphanumeric, hyphen, and underscore "
            f"characters."
        )

    # Ensure provided modules are valid
    modules = list(modules)
    for module in modules:
        if not ctx.modules.data.get(module, False):
            raise err.UserError(
                f"Invalid module: '{module}'. It was not found "
                f"in the Minitrino library at {ctx.minitrino_lib_dir}"
            )

    set_distribution(image)
    if not modules:
        ctx.logger.info(
            f"No modules specified. Provisioning standalone (coordinator-only) "
            f"{ctx.env.get('CLUSTER_DIST').title()} cluster..."
        )

    utils.check_daemon(ctx.docker_client)
    utils.check_lib(ctx)
    check_cluster_ver()
    check_version_requirements(modules)
    modules = append_running_modules(modules)
    modules = utils.check_dependent_modules(ctx, modules)
    runner(modules, workers, no_rollback, docker_native)

    dependent_clusters = check_dependent_clusters(modules)
    for cluster in dependent_clusters:
        runner(no_rollback=no_rollback, cluster=cluster)


@pass_environment
def runner(
    ctx: Environment,
    modules=[],
    workers=0,
    no_rollback=False,
    docker_native="",
    cluster={},
):
    """Runs the provision command."""

    ctx.logger.info(
        f"Starting {ctx.env.get('CLUSTER_DIST').title()} cluster provisioning..."
    )

    # If a dependent cluster is being provisioned, we need to grab the cluster's
    # modules and workers, then update the environment variables so that the
    # Compose YAMLs use the correct values.
    if cluster:
        ctx.logger.info(f"Provisioning dependent cluster: {cluster['name']}...")
        modules = cluster.get("modules", [])
        workers = cluster.get("workers", 0)
        ctx.cluster_name = cluster.get("name", "")
        ctx.env.update({"CLUSTER_NAME": ctx.cluster_name})
        ctx.env.update(
            {"COMPOSE_PROJECT_NAME": utils.get_compose_project_name(ctx.cluster_name)}
        )

    ctx.provisioned_clusters.append(ctx.cluster_name)

    check_compatibility(modules)
    check_enterprise(modules)
    check_volumes(modules)
    set_external_ports(modules)

    try:
        cmd_chunk = chunk(modules)
        compose_cmd = build_command(docker_native, cmd_chunk)
        ctx.cmd_executor.execute_commands(compose_cmd, environment=ctx.env.copy())

        execute_bootstraps(modules)
        write_cluster_cfg(modules)
        check_dup_cfgs()
        provision_workers(workers)
        ctx.logger.info(f"Environment provisioning complete.")

    except Exception as e:
        rollback(no_rollback)
        utils.handle_exception(e)


@pass_environment
def check_cluster_ver(ctx: Environment):
    """Checks if a proper cluster version is provided."""

    cluster_dist = ctx.env.get("CLUSTER_DIST", "")
    cluster_ver = ctx.env.get("CLUSTER_VER", "")

    if cluster_dist == "starburst":
        error_msg = (
            f"Provided Starburst version '{cluster_ver}' is invalid. "
            f"The version must be {MIN_CLUSTER_VER}-e or higher."
        )
        try:
            cluster_ver_int = int(cluster_ver[0:3])
            if cluster_ver_int < MIN_CLUSTER_VER or "-e" not in cluster_ver:
                raise err.UserError(error_msg)
        except:
            raise err.UserError(error_msg)
    elif cluster_dist == "trino":
        error_msg = (
            f"Provided Trino version '{cluster_ver}' is invalid. "
            f"The version must be {MIN_CLUSTER_VER} or higher."
        )
        if "-e" in cluster_ver:
            raise err.UserError(
                f"The provided Trino version '{cluster_ver}' cannot contain '-e'. "
                "Did you mean to use Starburst via the --image option?"
            )
        try:
            cluster_ver_int = int(cluster_ver[0:3])
            if cluster_ver_int < MIN_CLUSTER_VER:
                raise err.UserError(error_msg)
        except:
            raise err.UserError(error_msg)


@pass_environment
def check_version_requirements(ctx: Environment, modules=[]):
    """Checks for cluster version validity per version requirements defined in
    module metadata."""

    for module in modules:
        versions = ctx.modules.data.get(module, {}).get("versions", [])

        if not versions:
            continue
        if len(versions) > 2:
            raise err.UserError(
                f"Invalid versions specification for module '{module}' in metadata.json file: {versions}",
                f'The valid structure is: {{"versions": [min-ver, max-ver]}}. If the versions key is '
                f"present, the minimum version is required, and the maximum version is optional.",
            )

        cluster_ver = int(ctx.env.get("CLUSTER_VER", "")[0:3])
        min_ver = int(versions.pop(0))
        max_ver = None
        if versions:
            max_ver = int(versions.pop())

        begin_msg = (
            f"The supplied cluster version {cluster_ver} is incompatible with module '{module}'. "
            f"Per the module's metadata.json file, the"
        )

        if cluster_ver < min_ver:
            raise err.UserError(
                f"{begin_msg} minimum required cluster version for the module is: {min_ver}."
            )
        if max_ver and cluster_ver > max_ver:
            raise err.UserError(
                f"{begin_msg} maximum required cluster version for the module is: {max_ver}."
            )


@pass_environment
def check_dependent_clusters(ctx: Environment, modules=[]):
    """Checks if any of the provided modules have dependent clusters and returns
    a list of those clusters."""

    ctx.logger.verbose("Checking for dependent clusters...")
    dependent_clusters = []
    for module in modules:
        module_dependent_clusters = ctx.modules.data.get(module, {}).get(
            "dependentClusters", []
        )
        if module_dependent_clusters:
            for cluster in module_dependent_clusters:
                cluster["name"] = f"module-dep-{cluster['name']}"
                dependent_clusters.append(cluster)
    return list(dependent_clusters)


@pass_environment
def set_distribution(ctx: Environment, image=""):
    """Determines the distribution type (Trino or Starburst) based on the provided
    image type and sets distro-specific env variables. If the image is not specified,
    it defaults to Trino."""

    if not image:
        image = ctx.env.get("IMAGE", "trino")
    if image != "trino" and image != "starburst":
        raise err.UserError(
            f"Invalid image type '{image}'. Please specify either 'trino' or 'starburst'.",
            f"Example: `minitrino provision -i trino`. This can also be set permanently via "
            f"`minitrino config`.",
        )

    ctx.env.update({"CLUSTER_DIST": image})
    ctx.env.update({"BUILD_USER": image})
    ctx.env.update({"ETC": f"/etc/{image}"})


@pass_environment
def append_running_modules(ctx: Environment, modules=[]):
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
    modules.extend(running_modules.keys())
    return list(set(modules))


@pass_environment
def check_compatibility(ctx: Environment, modules=[]):
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
def check_enterprise(ctx: Environment, modules=[]):
    """Checks if any of the provided modules are Starburst Enterprise features.
    If they are, we confirm that a SEP license is provided."""

    ctx.logger.verbose(
        "Checking for Starburst Enterprise modules...",
    )

    yaml_path = os.path.join(ctx.minitrino_lib_dir, "docker-compose.yaml")
    with open(yaml_path) as f:
        yaml_file = yaml.load(f, Loader=yaml.FullLoader)
    volumes = yaml_file.get("services", {}).get("minitrino", {}).get("volumes", [])

    if LIC_VOLUME_MOUNT not in volumes:
        raise err.UserError(
            f"The required license volume in the library's root docker-compose.yaml "
            f"is either commented out or deleted: {yaml_path}. For reference, "
            f"the proper volume mount is: '{LIC_VOLUME_MOUNT}'"
        )

    enterprise_modules = []
    for module in modules:
        if ctx.modules.data.get(module, {}).get("enterprise", False):
            enterprise_modules.append(module)

    if enterprise_modules:
        if not ctx.env.get("CLUSTER_DIST") == "starburst":
            raise err.UserError(
                f"Module(s) {enterprise_modules} are only compatible with "
                f"Starburst Enterprise. Please specify the image type with the '-i' option. "
                f"Example: `minitrino provision -i starburst`",
            )
        if not ctx.env.get("LIC_PATH", False):
            raise err.UserError(
                f"Module(s) {enterprise_modules} requires a Starburst license. "
                f"You must provide a path to a Starburst license via the "
                f"LIC_PATH environment variable."
            )
        ctx.env.update({"LIC_MOUNT_PATH": LIC_MOUNT_PATH})
    elif ctx.env.get("LIC_PATH", False):
        ctx.env.update({"LIC_MOUNT_PATH": LIC_MOUNT_PATH})
    else:
        ctx.env.update({"LIC_PATH": "./modules/resources/dummy.license"})
        ctx.env.update({"LIC_MOUNT_PATH": DUMMY_LIC_MOUNT_PATH})


@pass_environment
def check_volumes(ctx: Environment, modules=[]):
    """Removes `catalogs` volume if it exists, and also checks if any of
    the modules have persistent volumes and issues a warning to the user if so."""

    try:
        volume_name = f"{utils.get_compose_project_name(ctx.cluster_name)}_catalogs"
        ctx.logger.verbose(f"Removing '{volume_name}' volume if exists...")
        volume = ctx.docker_client.volumes.get(volume_name)
        volume.remove()
        ctx.logger.verbose(f"Removed '{volume_name}' volume.")
    except:
        pass

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
def get_module_services(ctx: Environment, modules=[]):
    """Get all services defined in the provided modules. Returns a list of
    services, each represented as a list containing the service key, service
    dictionary, and the YAML file path."""

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

    return services


@pass_environment
def set_external_ports(ctx: Environment, modules=[]):
    """Find the next free host port not used by Docker or the host for each
    container with a dynamic host port."""

    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("0.0.0.0", port)) == 0

    def is_docker_port_in_use(port):
        containers = ctx.docker_client.containers.list()
        for container in containers:
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            for binding in ports.values():
                if binding:
                    for b in binding:
                        if str(port) == b.get("HostPort"):
                            return True
        return False

    def find_next_available_port(default_port):
        candidate_port = default_port
        while is_port_in_use(candidate_port) or is_docker_port_in_use(candidate_port):
            ctx.logger.verbose(
                f"Port {candidate_port} is already in use. Finding the next available port..."
            )
            candidate_port += 1
        return candidate_port

    def assign_port(container_name, host_port_var, default_port):
        candidate_port = find_next_available_port(default_port)
        fq_container_name = get_fully_qualified_container_name(
            container_name,
        )
        ctx.logger.info(
            f"Found available port {candidate_port} for container '{fq_container_name}'. "
            f"The service can be reached at localhost:{candidate_port}."
        )
        ctx.logger.verbose(
            f"Setting environment variable {host_port_var} to {candidate_port}"
        )
        ctx.env.update({host_port_var: str(candidate_port)})

    # Handle the core Minitrino container
    assign_port("minitrino", "__PORT_MINITRINO", 8080)

    # Handle module-defined services
    services = get_module_services(modules)
    for service in services:
        port_mappings = service[1].get("ports", [])
        container_name = service[1].get("container_name", "undefined")

        for port_mapping in port_mappings:
            if not "__PORT" in port_mapping:
                continue

            host_port_var, default_port = port_mapping.split(":")
            # Remove ${} syntax from the environment variable name
            host_port_var_name = re.sub(r"\$\{([^}]+)\}", r"\1", host_port_var)

            try:
                isinstance(int(default_port), int)
            except ValueError as e:
                raise err.UserError(
                    f"Default port '{default_port}' is not a valid integer. "
                    f"Please check the module's Docker Compose YAML file for the "
                    f"correct variable name and ensure a default value is "
                    f"set as an environment variable. See the wiki for more "
                    f"information: TODO: link\n{e}",
                )

            assign_port(container_name, host_port_var_name, int(default_port))


@pass_environment
def chunk(ctx: Environment, modules=[]):
    """Builds docker compose command chunk for the chosen modules. Returns a
    command chunk string."""

    chunk = []
    for module in modules:
        yaml_file = ctx.modules.data.get(module, {}).get("yaml_file", "")
        chunk.extend(f"-f {yaml_file} \\\n")
    return "".join(chunk)


@pass_environment
def build_command(ctx: Environment, docker_native="", chunk=""):
    """Builds a formatted docker compose command for shell execution. Returns a
    docker compose command string."""

    cmd = []
    cmd.extend(
        [
            "docker compose -f ",
            os.path.join(ctx.minitrino_lib_dir, "docker-compose.yaml"),
            " \\\n",
            chunk,  # Module YAML paths
            "up -d --force-recreate",
        ]
    )

    if docker_native:
        ctx.logger.verbose(
            f"Received native Docker Compose options: '{docker_native}'",
        )
        cmd.extend([" ", docker_native])
    return "".join(cmd)


@pass_environment
def execute_bootstraps(ctx: Environment, modules=[]):
    """Executes bootstrap scripts in module containers. After a bootstrap
    script is executed, the container it was executed in is restarted."""

    services = get_module_services(modules)

    # Get all container names for each service
    for service in services:
        bootstrap = service[1].get("environment", {}).get("MINITRINO_BOOTSTRAP")
        if bootstrap is None:
            continue
        container_name = service[1].get("container_name", "")
        if not container_name:
            # If there is not container name, the service name becomes the name
            # of the container
            container_name = service[0]
        fq_container_name = get_fully_qualified_container_name(
            container_name,
        )
        execute_container_bootstrap(bootstrap, fq_container_name, service[2])
        utils.restart_containers(ctx, [fq_container_name])


@pass_environment
def execute_container_bootstrap(
    ctx: Environment, bootstrap="", fq_container_name="", yaml_file=""
):
    """Executes a single bootstrap inside a container."""

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

    ctx.logger.verbose(
        f"Executing bootstrap script in container '{fq_container_name}'...",
    )

    ctx.cmd_executor.execute_commands(
        f"docker cp {bootstrap_file} {fq_container_name}:/tmp/"
    )

    ctx.cmd_executor.execute_commands(
        f"/tmp/{os.path.basename(bootstrap_file)}",
        container=get_container(fq_container_name),
    )

    ctx.logger.verbose(
        f"Successfully executed bootstrap script in container '{fq_container_name}'.",
    )


def split_cfg(cfgs=""):
    cfgs = cfgs.strip().split("\n")
    for i, cfg in enumerate(cfgs):
        cfg = re.sub(r"\s*=\s*", "=", cfg)
        cfgs[i] = cfg.split("=", 1)
    return cfgs


@pass_environment
def get_current_cfgs(ctx: Environment):
    """Get config.properties and jvm.config files. Return the two sets of
    configs as lists, e.g.:

    [['a', 'b'], ['c', 'd'], ['e', 'f']]
    """

    fq_container_name = get_fully_qualified_container_name("minitrino")
    current_cfgs = ctx.cmd_executor.execute_commands(
        f"bash -c 'cat {ETC_DIR}/{CLUSTER_CONFIG}'",
        f"bash -c 'cat {ETC_DIR}/{CLUSTER_JVM_CONFIG}'",
        container=get_container(fq_container_name),
        suppress_output=True,
    )

    current_cluster_cfgs = split_cfg(current_cfgs[0].get("output", ""))
    current_jvm_cfg = split_cfg(current_cfgs[1].get("output", ""))

    return current_cluster_cfgs, current_jvm_cfg


@pass_environment
def write_cluster_cfg(ctx: Environment, modules=[]):
    """Appends cluster config from various modules if specified in the module YAML
    file. The Minitrino coordinator container is restarted if any configs are
    written."""

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

    fq_container_name = get_fully_qualified_container_name("minitrino")
    coordinator = get_container(fq_container_name)

    if not coordinator:
        raise err.MinitrinoError(
            f"Attempting to append cluster config in Minitrino container, "
            f"but no running container was found."
        )

    cfgs = []
    jvm_cfg = []
    modules.append("minitrino")  # check if user placed configs in root compose yaml

    # Check configs passed through env variables
    env_usr_cfgs = ctx.env.get("CONFIG_PROPERTIES", "")
    env_user_jvm_cfg = ctx.env.get("JVM_CONFIG", "")

    if env_usr_cfgs:
        cfgs.extend(split_cfg(env_usr_cfgs))
    if env_user_jvm_cfg:
        jvm_cfg.extend(split_cfg(env_user_jvm_cfg))

    # Check configs passed through Docker Compose YAMLs
    for module in modules:
        if module == "minitrino":
            with open(os.path.join(ctx.minitrino_lib_dir, "docker-compose.yaml")) as f:
                yaml_file = yaml.load(f, Loader=yaml.FullLoader)
        else:
            yaml_file = ctx.modules.data.get(module, {}).get("yaml_dict")
        usr_cfgs = (
            yaml_file.get("services", {})
            .get("minitrino", {})
            .get("environment", {})
            .get("CONFIG_PROPERTIES", [])
        )
        user_jvm_cfg = (
            yaml_file.get("services", {})
            .get("minitrino", {})
            .get("environment", {})
            .get("JVM_CONFIG", [])
        )

        if usr_cfgs:
            cfgs.extend(split_cfg(usr_cfgs))
        if user_jvm_cfg:
            jvm_cfg.extend(split_cfg(user_jvm_cfg))

    if not cfgs and not jvm_cfg:
        return

    cfgs = handle_password_authenticators(cfgs)

    ctx.logger.verbose(
        "Checking coordinator server status before updating configs...",
    )

    retry = 0
    while retry <= 30:
        logs = coordinator.logs().decode()
        if "======== SERVER STARTED ========" in logs:
            ctx.logger.verbose(
                "Coordinator started.",
            )
            break
        elif coordinator.status != "running":
            raise err.MinitrinoError(
                f"The coordinator stopped running. Inspect the container logs if the "
                f"container is still available. If the container was rolled back, rerun "
                f"the command with the '--no-rollback' option, then inspect the logs."
            )
        else:
            ctx.logger.verbose(
                "Waiting for coordinator to start...",
            )
            time.sleep(1)
            retry += 1

    def append_cfgs(coordinator, usr_cfgs, current_cfgs, filename):
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
            f"bash -c 'rm {ETC_DIR}/{filename}'", container=coordinator
        )

        ctx.logger.verbose(
            f"Writing new config to {filename}...",
        )
        for current_cfg in current_cfgs:
            append_cfg = (
                f'bash -c "cat <<EOT >> {ETC_DIR}/{filename}\n{current_cfg}\nEOT"'
            )
            ctx.cmd_executor.execute_commands(
                append_cfg, container=coordinator, suppress_output=True
            )

    ctx.logger.verbose(
        "Appending user-defined config to cluster container config...",
    )

    current_cluster_cfgs, current_jvm_cfg = get_current_cfgs()
    append_cfgs(coordinator, cfgs, current_cluster_cfgs, CLUSTER_CONFIG)
    append_cfgs(coordinator, jvm_cfg, current_jvm_cfg, CLUSTER_JVM_CONFIG)

    utils.restart_containers(ctx, ["minitrino"])


@pass_environment
def check_dup_cfgs(ctx: Environment):
    """Checks for duplicate configs in cluster config files (jvm.config and
    config.properties). This is a safety check for modules that may improperly
    modify these files."""

    def log_duplicates(cfgs, filename):
        ctx.logger.verbose(
            f"Checking '{filename}' file for duplicate configs...",
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
                f"Duplicate configuration properties detected in "
                f"'{filename}' file:\n{str(duplicates)}",
            )

    current_cluster_cfgs, current_jvm_cfg = get_current_cfgs()

    log_duplicates(current_cluster_cfgs, CLUSTER_CONFIG)
    log_duplicates(current_jvm_cfg, CLUSTER_JVM_CONFIG)


@pass_environment
def provision_workers(ctx: Environment, workers=0):
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
    pattern = rf"minitrino-worker-\d+-{ctx.cluster_name}"
    worker_containers = [
        c.name
        for c in containers
        if re.match(pattern, c.name)
        if c.name.startswith("minitrino-worker-")
        and c.labels.get("org.minitrino") == "root"
    ]

    # Scenario 1
    if workers == 0 and len(worker_containers) == 0:
        return
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
            c = get_container(c)
            c.kill()
            c.remove()
            identifier = utils.generate_identifier({"ID": c.short_id, "Name": c.name})
            ctx.logger.warn(f"Removed excess worker: {identifier}")

    worker_img = (
        f"minitrino/cluster:{ctx.env.get('CLUSTER_VER')}-{ctx.env.get('CLUSTER_DIST')}"
    )

    compose_project_name = utils.get_compose_project_name(ctx.cluster_name)
    network_name = f"minitrino_{ctx.cluster_name}"
    fq_container_name = get_fully_qualified_container_name("minitrino")
    coordinator = get_container(fq_container_name)

    restart = []
    for i in range(1, workers + 1):
        fq_worker_name = get_fully_qualified_container_name(
            f"minitrino-worker-{i}",
        )
        try:
            worker = get_container(fq_worker_name)
        except NotFound:
            worker = ctx.docker_client.containers.run(
                worker_img,
                name=fq_worker_name,
                detach=True,
                network=network_name,
                labels={
                    "org.minitrino": "root",
                    "org.minitrino.module": "minitrino",
                    "com.docker.compose.project": compose_project_name,
                    "com.docker.compose.service": "minitrino-worker",
                },
            )
            ctx.logger.verbose(
                f"Created and started worker container: '{fq_worker_name}' in network '{network_name}'"
            )

        user = ctx.env.get("BUILD_USER")
        tar_path = "/tmp/${CLUSTER_DIST}.tar.gz"

        # Copy the source directory from the coordinator to the worker container
        ctx.cmd_executor.execute_commands(
            f"bash -c 'tar czf {tar_path} -C /etc ${{CLUSTER_DIST}}'",
            container=coordinator,
            docker_user=user,
        )

        # Copy the tar file from the coordinator container
        bits, _ = coordinator.get_archive(f"/tmp/{ctx.env.get('CLUSTER_DIST')}.tar.gz")
        tar_stream = b"".join(bits)

        worker.put_archive("/tmp", tar_stream)

        # Put the tar file into the new worker container & extract
        ctx.cmd_executor.execute_commands(
            f"bash -c 'tar xzf {tar_path} -C /etc'",
            container=worker,
            docker_user=user,
        )

        # Overwrite worker config.properties
        ctx.cmd_executor.execute_commands(
            f"bash -c \"echo '{WORKER_CONFIG_PROPS}' > {ETC_DIR}/{CLUSTER_CONFIG}\"",
            container=worker,
            docker_user=user,
        )

        restart.append(fq_worker_name)
        ctx.logger.verbose(f"Copied {ETC_DIR} to '{fq_worker_name}'")

    utils.restart_containers(ctx, restart)


@pass_environment
def get_fully_qualified_container_name(ctx: Environment, name=""):
    """Returns the fully qualified container name based on the provided
    container and cluster name."""

    # If we receive a container name with a literal suffix `-${CLUSTER_NAME}`,
    # remove it. In this case, the container name was sourced from the Docker
    # Compose file directly, which preserves the literal suffix. We need to
    # dynamically append the suffix based on the cluster name.
    if "-${CLUSTER_NAME}" in name:
        name = name.replace("-${CLUSTER_NAME}", "")
    return f"{name}-{ctx.cluster_name}"


@pass_environment
def get_container(ctx: Environment, fully_qualified_name=""):
    """Returns a Docker container object based on the provided fully qualified
    container name."""
    return ctx.docker_client.containers.get(fully_qualified_name)


@pass_environment
def rollback(ctx: Environment, no_rollback=False):
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

    for cluster in ctx.provisioned_clusters:
        ctx.logger.warn(f"Rolling back cluster: {cluster}...")
        resources = ctx.get_cluster_resources(cluster_name=cluster)
        containers = resources["containers"]
        for container in containers:
            for action in (container.kill, container.remove):
                try:
                    action()
                except:
                    pass
