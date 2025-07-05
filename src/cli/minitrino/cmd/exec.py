"""Docker Exec wrapper."""

import click
from docker.errors import APIError, NotFound

from minitrino import utils
from minitrino.core.cluster.resource import MinitrinoContainer
from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.exec.utils import detect_container_shell


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
        The command to execute inside the container.
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
    if interactive:
        try:
            result = ctx.cmd_executor.execute(
                cmd, interactive=interactive, suppress_output=True, trigger_error=False
            )[0]
        except Exception as e:
            raise MinitrinoError(f"Error while running TTY command in '{fqcn}': {e}")
        if result.exit_code not in [0, 130, 137]:
            raise MinitrinoError(
                f"Failed to execute TTY command in '{fqcn}':\n{cmd}\n"
                f"Exit code: {result.exit_code}\n"
                f"Command output: {result.output}"
            )
    else:
        for line in ctx.cmd_executor.stream_execute(
            cmd, interactive=interactive, suppress_output=True
        ):
            if line.strip():
                ctx.logger.info(line)


@utils.pass_environment()
def build_cmd(
    ctx: MinitrinoContext, command: tuple, fqcn: str, user: str, interactive: bool
) -> list[str]:
    """Build the docker exec command.

    Parameters
    ----------
    ctx : MinitrinoContext
        The CLI context object.
    command : tuple
        The command to execute inside the container.
    fqcn : str
        Fully qualified container name.
    user : str
        Username or UID to run the command as.
    interactive : bool
        If True, runs the command in interactive mode.

    Returns
    -------
    list[str]
        The full docker exec command as a list of arguments.
    """
    shell = detect_container_shell(ctx, fqcn, user)
    base_cmd = ["docker", "exec", "-u", user]
    if interactive:
        base_cmd.append("-it")
    base_cmd.append(fqcn)
    if command:
        shell_cmd = " ".join(command)
        full_cmd = base_cmd + [shell, "-l", "-c", shell_cmd]
    else:
        full_cmd = base_cmd + [shell]
    return full_cmd
