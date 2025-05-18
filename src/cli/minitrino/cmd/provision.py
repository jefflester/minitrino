"""Provisioning commands for Minitrino CLI."""

import os
import stat
import click

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import UserError

from typing import Optional


@click.command(
    "provision",
    help="Provision a cluster with optional modules.",
)
@click.option(
    "-m",
    "--module",
    "modules",
    default=[],
    type=str,
    multiple=True,
    help="Module to install in the cluster.",
)
@click.option(
    "-i",
    "--image",
    default="",
    type=str,
    help="Cluster image type (trino or starburst). Defaults to trino.",
)
@click.option(
    "-w",
    "--workers",
    "workers",
    default=0,
    type=int,
    help="Number of cluster workers to provision (default: 0).",
)
@click.option(
    "-n",
    "--no-rollback",
    is_flag=True,
    default=False,
    help="Disables cluster rollback if provisioning fails.",
)
@click.option(
    "-d",
    "--docker-native",
    default="",
    type=str,
    help=(
        """Append Docker Compose commands to the underlying docker compose
        command. All valid `docker compose up` options are supported, e.g.:

        `minitrino provision --docker-native --build`\n\n`minitrino provision
        --docker-native '--remove-orphans --force-recreate'`"""
    ),
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext,
    modules: tuple[str, ...],
    image: str,
    workers: int,
    no_rollback: bool,
    docker_native: str,
) -> None:
    """Provision the environment with the specified modules and settings.

    If no options are provided, a standalone coordinator is provisioned. Supports Trino
    or Starburst distributions, dynamic worker scaling, and native Docker Compose
    arguments. Dependent clusters are automatically provisioned after the primary
    environment is launched.

    Parameters
    ----------
    modules : list[str]
        One or more modules to provision in the cluster.
    image : str
        Cluster image type (trino or starburst).
    workers : int
        Number of cluster workers to provision.
    no_rollback : bool
        If True, disables rollback on failure.
    docker_native : str
        Additional Docker Compose flags to append to the launch command.
    """
    # An asterisk is invalid in this context
    if ctx.all_clusters:
        raise UserError(
            "The `provision` command cannot interact with multiple/all clusters. "
            "Please specify a valid cluster name containing only alphanumeric, "
            "hyphen, and underscore characters."
        )

    # Ensure provided modules are valid
    modules_list = list(modules)
    for module in modules_list:
        if not ctx.modules.data.get(module, False):
            raise UserError(
                f"Invalid module: '{module}'. It was not found "
                f"in the Minitrino library at {ctx.lib_dir}"
            )

    set_distribution(image)
    if not modules_list:
        ctx.logger.info(
            f"No modules specified. Provisioning standalone (coordinator-only) "
            f"{ctx.env.get('CLUSTER_DIST').title()} cluster..."
        )

    utils.check_daemon(ctx.docker_client)
    utils.check_lib(ctx)
    ctx.cluster.validator.check_cluster_ver()
    ctx.modules.check_module_version_requirements(modules_list)
    modules_list = append_running_modules(modules_list)
    modules_list = ctx.modules.check_dep_modules(modules_list)
    runner(modules_list, workers, no_rollback, docker_native)

    dependent_clusters = ctx.cluster.validator.check_dependent_clusters(modules_list)
    for cluster in dependent_clusters:
        runner(no_rollback=no_rollback, cluster=cluster)

    ctx.logger.info(f"Environment provisioning complete.")


@utils.pass_environment()
def runner(
    ctx: MinitrinoContext,
    modules: Optional[list[str]] = None,
    workers: int = 0,
    no_rollback: bool = False,
    docker_native: str = "",
    cluster: Optional[dict] = None,
) -> None:
    """Execute the provisioning flow for a given cluster and module set.

    If provisioning a dependent cluster, updates the cluster context and environment
    variables before executing the provisioning steps.

    Parameters
    ----------
    modules : list[str], optional
        The modules to provision. Defaults to an empty list if not provided.
    workers : int, optional
        The number of workers to provision. Defaults to 0.
    no_rollback : bool, optional
        Whether rollback should be skipped on failure. Defaults to False.
    docker_native : str, optional
        Additional Docker Compose flags to include. Defaults to an empty string.
    cluster : dict, optional
        Optional dictionary representing a dependent cluster configuration. Defaults to
        None.
    """
    if modules is None:
        modules = []
    if cluster is None:
        cluster = {}

    ctx.logger.info(
        f"Starting {ctx.env.get('CLUSTER_DIST').title()} cluster provisioning..."
    )

    # If a dependent cluster is being provisioned, we need to grab the cluster's modules
    # and workers, then update the environment variables so that the Compose YAMLs use
    # the correct values.
    if cluster:
        ctx.logger.info(f"Provisioning dependent cluster: {cluster['name']}...")
        modules = cluster.get("modules", [])
        workers = cluster.get("workers", 0)
        ctx.cluster_name = cluster.get("name", "")
        ctx.env.update({"CLUSTER_NAME": ctx.cluster_name})
        ctx.env.update(
            {"COMPOSE_PROJECT_NAME": ctx.cluster.resource.compose_project_name()}
        )

    ctx.provisioned_clusters.append(ctx.cluster_name)

    ctx.modules.check_enterprise(modules)
    ctx.modules.check_compatibility(modules)
    ctx.modules.check_volumes(modules)
    ctx.cluster.config.set_external_ports(modules)

    try:
        cmd_chunk = chunk(modules)
        compose_cmd = build_command(docker_native, cmd_chunk)
        ctx.cmd_executor.execute(compose_cmd, environment=ctx.env.copy())

        execute_bootstraps(modules)
        ctx.cluster.config.write_config(modules)
        ctx.cluster.validator.check_dup_config()
        ctx.cluster.ops.provision_workers(workers)

    except Exception as e:
        rollback(ctx, no_rollback)
        raise e


@utils.pass_environment()
def set_distribution(ctx: MinitrinoContext) -> None:
    """Determine the cluster distribution.

    Set the distribution for the cluster based on the configuration.
    """
    image = ctx.env.get("IMAGE", "trino")
    if image != "trino" and image != "starburst":
        raise UserError(
            f"Invalid image type '{image}'. Please specify either 'trino' or 'starburst'.",
            f"Example: `minitrino provision -i trino`. This can also be set permanently via "
            f"`minitrino config`.",
        )

    ctx.env.update({"CLUSTER_DIST": image})
    ctx.env.update({"BUILD_USER": image})
    ctx.env.update({"ETC": f"/etc/{image}"})


@utils.pass_environment()
def append_running_modules(ctx: MinitrinoContext) -> list[str]:
    """Check for running modules.

    Append running modules to the context.
    """
    ctx.logger.verbose("Checking for running modules...")
    running_modules = ctx.modules.running_modules()

    if running_modules:
        ctx.logger.verbose(
            f"Identified the following running modules: {list(running_modules.keys())}. "
            f"Appending the running module list to the list of modules to provision.",
        )

    modules = []
    modules.extend(running_modules.keys())
    return list(set(modules))


@utils.pass_environment()
def chunk(ctx: MinitrinoContext) -> str:
    """Construct a chunk of configuration.

    Constructs a docker compose command chunk for the specified modules.
    """
    modules = ctx.modules.data.keys()
    chunk: list[str] = []
    for module in modules:
        yaml_file = ctx.modules.data.get(module, {}).get("yaml_file", "")
        chunk.extend(f"-f {yaml_file} \\\n")
    return "".join(chunk)


@utils.pass_environment()
def build_command(
    ctx: MinitrinoContext, docker_native: str = "", chunk: str = ""
) -> str:
    """Build the cluster command.

    Builds a formatted docker compose command string for shell execution.
    """
    cmd = []
    cmd.extend(
        [
            "docker compose -f ",
            os.path.join(ctx.lib_dir, "docker-compose.yaml"),
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


@utils.pass_environment()
def execute_bootstraps(
    ctx: MinitrinoContext, modules: Optional[list[str]] = None
) -> None:
    """Execute bootstrap scripts.

    Run all bootstrap scripts for the cluster.
    """
    if modules is None:
        modules = []

    services = ctx.modules.module_services(modules)

    # Get all container names for each service
    for service in services:
        bootstrap = service[1].get("environment", {}).get("MINITRINO_BOOTSTRAP")
        if bootstrap is None:
            continue
        container_name = service[1].get("container_name", "")
        if not container_name:
            # If there is no container name, the service name becomes the name of the
            # container
            container_name = service[0]
        fq_container_name = ctx.cluster.resource.fq_container_name(container_name)
        execute_container_bootstrap(ctx, bootstrap, fq_container_name, service[2])
        ctx.cluster.ops.restart_containers([fq_container_name])


@utils.pass_environment()
def execute_container_bootstrap(
    ctx: MinitrinoContext,
    bootstrap: str = "",
    fq_container_name: str = "",
    yaml_file: str = "",
) -> None:
    """Execute a container bootstrap.

    Executes a single bootstrap script inside a specified container.
    """
    bootstrap_file = os.path.join(
        os.path.dirname(yaml_file), "resources", "bootstrap", bootstrap
    )
    if not os.path.isfile(bootstrap_file):
        raise UserError(
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

    ctx.cmd_executor.execute(f"docker cp {bootstrap_file} {fq_container_name}:/tmp/")

    ctx.cmd_executor.execute(
        f"/tmp/{os.path.basename(bootstrap_file)}",
        container=ctx.cluster.resource.container(fq_container_name),
    )

    ctx.logger.verbose(
        f"Successfully executed bootstrap script in container '{fq_container_name}'.",
    )


@utils.pass_environment()
def rollback(ctx: MinitrinoContext, no_rollback: bool = False) -> None:
    """Perform a rollback operation.

    Roll back the cluster to a previous state.     Defaults to False.
    """
    if no_rollback:
        ctx.logger.warn(
            f"Errors occurred during cluster '{ctx.cluster_name}' provisioning and "
            f"rollback has been disabled. Provisioned resources will remain in an "
            f"unaltered state.",
        )
        return

    for cluster in ctx.provisioned_clusters:
        ctx.cluster_name = cluster  # Activate the cluster in the context
        ctx.cluster.ops.rollback()
