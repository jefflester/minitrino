"""Docker Exec wrapper."""

import shlex

import click
from docker.errors import APIError, NotFound

from minitrino import utils
from minitrino.core.cluster.resource import MinitrinoContainer
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError, UserError


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
    "-u",
    "--user",
    default="root",
    type=str,
    help="Username or UID",
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
    ctx: MinitrinoContext, command: tuple, container: str, user: str, interactive: bool
) -> None:
    """
    Run a command in a container.

    Parameters
    ----------
    command : tuple
        The command to run in the container.
    container : str
        The container to run the command in.
    user : str
        Username or UID to run the command as.
    interactive : bool
        If True, runs the command in interactive mode.
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
    cmd = build_cmd(command, fqcn, user, interactive)
    try:
        result = ctx.cmd_executor.execute(
            cmd, interactive=interactive, suppress_output=True
        )[0]
    except MinitrinoError as e:
        if "Exit code: 137" in str(e) or "is not running" in str(e):
            raise UserError(
                f"Container '{fqcn}' is not running or was stopped.",
                "Start the container and try again.",
            )
        else:
            raise e
    if not interactive:
        if result.output.strip():
            ctx.logger.info(result.output)


@utils.pass_environment()
def build_cmd(
    ctx: MinitrinoContext, command: tuple, fqcn: str, user: str, interactive: bool
) -> str:
    """Build the docker exec command."""
    it = "-it" if interactive else ""
    shell = detect_container_shell(ctx.cluster.resource.container(fqcn), user)
    cmd_str = " ".join(command) if command else shell
    cmd = (
        f"docker exec -u {user}"
        f"{f' {it}' if it else ''} "
        f"{fqcn} {shell} -c {shlex.quote(cmd_str)}"
    )
    return cmd


@utils.pass_environment()
def detect_container_shell(
    ctx: MinitrinoContext, container: MinitrinoContainer, user: str
):
    """Detect the shell in the container."""
    try:
        result = ctx.cmd_executor.execute(
            "which bash",
            container=container,
            docker_user=user,
        )
        if result and result[0].output.strip():
            return "/bin/bash"
    except Exception:
        pass
    try:
        result = ctx.cmd_executor.execute(
            "which sh",
            container=container,
            docker_user=user,
        )
        if result and result[0].output.strip():
            return "/bin/sh"
    except Exception:
        pass
    raise MinitrinoError(
        f"No supported shell found in container '{container.name}'. "
        "Install /bin/sh or /bin/bash in the container image.",
    )
