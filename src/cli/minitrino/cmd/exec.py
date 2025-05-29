"""Docker Exec wrapper."""

import click
from docker.errors import APIError, NotFound

from minitrino import utils
from minitrino.core.cluster.resource import MinitrinoContainer
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import UserError


@click.command(
    "exec",
    help="Run a command in a container (default command is /bin/bash).",
)
@click.argument(
    "command",
    nargs=-1,
    required=False,
)
@click.option(
    "-c",
    "--container",
    default="",
    type=str,
    help=(
        "Container to run the command in (defaults to "
        "current cluster's coordinator container)."
    ),
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    default=False,
    help="Run the command in an interactive shell.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext, command: tuple, container: str, interactive: bool
) -> None:
    """
    Run a command in a container.

    Parameters
    ----------
    command : tuple
        The command to run in the container.
    container : str
        The container to run the command in.
    """
    ctx.initialize()
    if ctx.all_clusters:
        raise UserError(
            "Cannot run exec on all clusters.",
            "Provide a specific cluster and try again.",
        )
    if not container:
        fqcn = ctx.cluster.resource.fq_container_name("minitrino")
    elif f"-{ctx.cluster_name}" in container:
        fqcn = ctx.cluster.resource.fq_container_name(
            container.replace(f"-{ctx.cluster_name}", "")
        )
    else:
        fqcn = ctx.cluster.resource.fq_container_name(container)
    try:
        c = ctx.cluster.resource.container(fqcn)
        assert isinstance(c, MinitrinoContainer)
    except (AssertionError, NotFound, APIError):
        raise UserError(
            f"Container '{fqcn}' not found or not running.",
            "Provide a valid container name and try again.",
        )
    it = "-it" if interactive else ""
    command = " ".join(command) if command else "/bin/bash"
    cmd = f"docker exec{f' {it}' if it else ''} {fqcn} {command}"
    output = ctx.cmd_executor.execute(
        cmd, interactive=interactive, suppress_output=True
    )[0].output
    ctx.logger.info(output)
