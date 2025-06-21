"""Common utilities for Minitrino integration and system tests."""

import logging
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Dict, Optional, TypedDict

import docker
from click.testing import CliRunner, Result
from docker.models.containers import Container

from minitrino.cli import cli
from minitrino.core.cmd_exec import CommandExecutor
from minitrino.core.docker.socket import resolve_docker_socket
from minitrino.settings import ROOT_LABEL

USER_HOME_DIR = os.path.expanduser("~")
MINITRINO_USER_DIR = os.path.abspath(os.path.join(USER_HOME_DIR, ".minitrino"))
CONFIG_FILE = os.path.abspath(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg"))
MINITRINO_LIB_DIR = os.path.join(
    Path(os.path.abspath(__file__)).resolve().parents[2], "lib"
)

# ------------------------
# Misc Utilities
# ------------------------


def get_logger() -> logging.Logger:
    """Get the logger for the test module."""
    logger = logging.getLogger("minitrino.test")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(levelname)-8s %(name)s:%(filename)s:%(lineno)d %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = get_logger()


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from a string."""
    return CommandExecutor._strip_ansi(text)


# ------------------------
# CLI Command Helpers
# ------------------------


class BuildCmdArgs(TypedDict, total=False):
    """Arguments for build_cmd."""

    base: str
    cluster: str
    append: list[str]
    prepend: list[str]
    verbose: bool


class CLICommandBuilder:
    """Build a CLI command for CliRunner.

    Parameters
    ----------
    cluster : str
        The cluster name to use.
    """

    def __init__(self, cluster: str):
        self.cluster = cluster

    def build_cmd(
        self,
        base: str = "",
        cluster: str = "",
        append: list[str] = [],
        prepend: list[str] = [],
        verbose: bool = True,
    ) -> list[str]:
        """
        Build a CLI command for CliRunner.

            [minitrino (<impl>)] [-v] [--cluster <cluster>] <prepend>
            <base> <append>

        Parameters
        ----------
        base : str
            The base command (e.g. 'down', 'remove').
        cluster : str
            The cluster name to use. Defaults to the cluster name
            specified in the constructor.
        append : list[str]
            Extra arguments to add to the command after the base
            command.
        prepend : list[str]
            Extra arguments to add to the command before the base
            command.
        verbose : bool
            Whether to add the '-v' and '--global-logging' flags to the
            command. Defaults to `True`.

        Returns
        -------
        list[str]
            The built command.

        Examples
        --------
        >>> build_cmd("down")
        ["-v", "--cluster", "cli-test", "down"]
        >>> build_cmd("down", cluster="cli-test-2")
        ["-v", "--cluster", "cli-test-2", "down"]
        >>> build_cmd("down", append=["--sig-kill"], prepend=["--env", "FOO=bar"])
        ["-v", "--cluster", "cli-test", "--env", "FOO=bar", "down", "--sig-kill"]
        """
        cmd = ["--cluster", cluster or self.cluster, *prepend, base, *append]
        if verbose:
            cmd = ["-v", "--global-logging"] + cmd
        if base == "provision":
            # Always build if there are local changes
            cmd.append("--build")
        return cmd


def cli_cmd(
    cmd: list[str],
    input: str | None = None,
    env: Optional[Dict[str, str]] = None,
    log_output: bool = True,
) -> Result:
    """
    Log and execute a CLI command.

    Parameters
    ----------
    cmd : list[str]
        The command and arguments to invoke.
    input : str | None
        Input string to pass to the command (for prompts, etc.).
        Defaults to None.
    env : Optional[Dict[str, str]]
        Environment variables to set for the command. Defaults to an
        empty dict.
    log_output : bool
        Whether to log the output of the command. Defaults to `True`.

    Returns
    -------
    Result
        The Click testing Result object.
    """
    msg = "Invoking CLI command '%s' %s"
    logger.info(
        msg
        % (
            f"minitrino {' '.join(cmd) if cmd else ''}",
            " with input: %s" % input if input else "",
        )
    )
    runner = CliRunner()
    env = env or {}
    result = runner.invoke(cli, cmd, input=input, env=env)
    if log_output:
        logger.info(f"Result output:\n{result.output}")
    return result


# ------------------------
# Docker Helpers
# ------------------------


def is_docker_running(logger: Optional[logging.Logger] = None) -> bool:
    """
    Check if the Docker daemon is currently running and accessible.

    Parameters
    ----------
    logger : Optional[logging.Logger]
        The logger to use for logging.

    Returns
    -------
    bool
        True if Docker is running and responding to a ping, False
        otherwise.
    """
    try:
        docker.DockerClient(base_url=resolve_docker_socket()).ping()
        return True
    except Exception as e:
        msg = f"Failed to ping Docker daemon: {e}"
        if not logger:
            logging.getLogger("minitrino.test").warning(msg)
        if logger:
            logger.warning(msg)
        return False


def try_start(cmd: list[str]) -> bool:
    """
    Attempt to start a process using the provided command.

    Parameters
    ----------
    cmd : list of str
        The command and arguments to execute.

    Returns
    -------
    bool
        True if the command executed successfully (exit code 0), False
        otherwise.
    """
    try:
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        result = execute_cmd(cmd=cmd_str)
        return result.exit_code == 0
    except Exception:
        return False


def start_docker_daemon(logger: Optional[logging.Logger] = None) -> None:
    """
    Start the Docker daemon on macOS or Linux.

    Parameters
    ----------
    logger : Optional[logging.Logger]
        The logger to use for logging.

    Raises
    ------
    RuntimeError
        If no supported Docker backend is found or the platform is
        unsupported.
    TimeoutError
        If the Docker daemon does not start within one minute.

    Notes
    -----
    Supports Docker Desktop, OrbStack, Colima, Rancher Desktop, etc.

    This function will detect the available Docker backend and attempt
    to start it if Docker is not already running. It waits up to 60
    seconds for Docker to become available.
    """
    if is_docker_running(logger):
        return

    started = False
    if sys.platform.lower() == "darwin":
        if shutil.which("docker") and shutil.which("open"):
            started = try_start(["open", "--background", "-a", "Docker"])
        if not started and shutil.which("orbstack"):
            started = try_start(["open", "-a", "OrbStack"])
        if not started and shutil.which("colima"):
            started = try_start(["colima", "start"])
        if not started and shutil.which("rancher-desktop"):
            started = try_start(["open", "-a", "Rancher Desktop"])
        if not started:
            raise RuntimeError(
                "No supported Docker backend found "
                "(Docker Desktop, OrbStack, Colima, Rancher Desktop)."
            )
    elif "linux" in sys.platform.lower():
        if shutil.which("systemctl"):
            started = try_start(["sudo", "systemctl", "start", "docker"])
        if not started and shutil.which("service"):
            started = try_start(["sudo", "service", "docker", "start"])
        if not started:
            raise RuntimeError(
                "Could not start Docker daemon (systemctl/service not available)."
            )
    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")

    for _ in range(60):
        if is_docker_running():
            return
        sleep(1)
    raise TimeoutError("Docker daemon failed to start after one minute.")


def try_stop(cmd: list[str]) -> bool:
    """
    Attempt to stop a process or service using the provided command.

    Parameters
    ----------
    cmd : list of str
        The command and arguments to execute.

    Returns
    -------
    bool
        True if the command executed successfully (exit code 0), False
        otherwise.
    """
    try:
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        result = execute_cmd(cmd=cmd_str)
        return result.exit_code == 0
    except Exception:
        return False


def force_quit_docker_backends():
    """
    Immediately quit all known Docker backends on macOS.

    Tries AppleScript for graceful quit, then killall for UI and backend
    processes. No sudo required. For Colima, uses 'colima stop'.
    """
    import shutil
    from time import sleep

    for app in ["Docker", "OrbStack", "Rancher Desktop"]:
        if shutil.which("osascript"):
            try:
                execute_cmd(cmd=f"osascript -e 'quit app \"{app}\"'")
            except Exception:
                pass
    sleep(2)
    for proc in [
        "Docker",
        "com.docker.backend",
        "com.docker.hyperkit",
        "OrbStack",
        "com.orbstack.backend",
        "com.orbstack.hyperkit",
        "Rancher Desktop",
        "lima",
        "qemu-system-aarch64",
        "qemu-system-x86_64",
    ]:
        try:
            execute_cmd(cmd=f"killall -9 {proc}")
        except Exception:
            pass
    if shutil.which("colima"):
        execute_cmd(cmd="colima stop")


def stop_docker_daemon() -> None:
    """
    Force-stop the Docker daemon.

    Raises
    ------
    RuntimeError
        If no supported Docker backend is found or the platform is
        unsupported.
    TimeoutError
        If the Docker daemon does not stop within one minute.
    """
    if sys.platform.lower() == "darwin":
        force_quit_docker_backends()
    elif "linux" in sys.platform.lower():
        stopped = False
        if shutil.which("systemctl"):
            stopped = try_stop(["sudo", "systemctl", "stop", "docker"])
        if not stopped and shutil.which("service"):
            stopped = try_stop(["sudo", "service", "docker", "stop"])
        if not stopped:
            cmd_str = " ".join(
                shlex.quote(arg) for arg in ["sudo", "killall", "-9", "dockerd"]
            )
            execute_cmd(cmd=cmd_str)

    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")

    for _ in range(10):
        if not is_docker_running():
            return
        sleep(1)
    raise TimeoutError("Docker daemon failed to stop after force quit.")


def get_containers(container_name: str = "", all: bool = False) -> list[Container]:
    """
    Fetch Minitrino containers.

    If a name is provided, return the container with the specified name.
    If no name is provided, return all containers.

    Parameters
    ----------
    container_name : str
        Name of the container to fetch.
    all : bool
        Whether to fetch all containers or only running containers.

    Returns
    -------
    list[Container]
        List of containers if `container_name` is not provided,
        otherwise the container with the specified name.

    Raises
    ------
    RuntimeError
        If the container is not found.
    """
    time.sleep(1)  # Avoid race condition
    docker_client = docker.DockerClient(base_url=resolve_docker_socket())

    containers: list[Container] = docker_client.containers.list(
        filters={"label": [ROOT_LABEL]}, all=all
    )
    if not container_name:
        return containers
    for container in containers:
        if container.name == container_name:
            return [container]
    raise RuntimeError(f"Container '{container_name}' not found")


def execute_in_coordinator(cmd: str = "", container_name: str = "") -> "CommandResult":
    """
    Execute a command in the coordinator container.

    Parameters
    ----------
    cmd : str
        The command to execute.

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit
        code.
    """
    from minitrino.utils import container_user_and_id

    _, uid = container_user_and_id(container=container_name)
    wrapped_cmd = f"bash -c {shlex.quote(cmd)}"
    return execute_cmd(wrapped_cmd, container_name, user=uid)


# ------------------------
# Command Helpers
# ------------------------


@dataclass
class CommandResult:
    """
    Command result.

    Attributes
    ----------
    command : str
        The command string that was executed.
    output : str
        The combined output of stdout and stderr.
    exit_code : int
        The exit code returned by the command.
    """

    command: str
    output: str
    exit_code: int


def execute_cmd(
    cmd: str = "",
    container: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    user: str = "root",
) -> CommandResult:
    """
    Execute a command in the user's shell or inside of a container.

    Parameters
    ----------
    cmd : str
        The command to execute.
    container : str, optional
        Container name to execute command inside of.
    env : dict[str, str], optional
        Environment variables to pass to the container.
    user : str, optional
        The user (or user ID) to execute the command as within the
        container. Defaults to `root`.

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit
        code.
    """
    env = env or {}
    if container:
        return _execute_in_container(cmd, container, env, user)
    else:
        return _execute_in_shell(cmd, env)


def _execute_in_shell(
    cmd: str = "", env: Optional[dict[str, str]] = None
) -> CommandResult:
    """
    Execute a command in the host shell.

    Parameters
    ----------
    cmd : str
        The command to execute.
    env : dict[str, str], optional
        Environment variables to use for the command.

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit
        code.
    """
    print(f"Executing command on host shell: {cmd}")

    env = env or {}
    process = subprocess.Popen(
        cmd,
        shell=True,
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        env={**os.environ, **env},
    )

    output = ""
    print("Command output:")
    if process.stdout is None:
        raise RuntimeError("Failed to execute command.")
    with process.stdout as p:
        for line in p:
            output += line
            print(line, end="")  # process line here
    process.wait()
    return CommandResult(cmd, output, process.returncode)


def _execute_in_container(
    cmd: str = "",
    container_name: str = "",
    env: Optional[dict[str, str]] = None,
    user: str = "root",
) -> CommandResult:
    """
    Execute a command inside of a container.

    Parameters
    ----------
    cmd : str
        The command to execute.
    container_name : str
        Name of the container to execute the command in.
    env : dict[str, str], optional
        Environment variables to use for the command.
    user : str, optional
        The user (or user ID) to execute the command as within the
        container. Defaults to `root`.

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit
        code.
    """
    api_client = docker.APIClient(base_url=resolve_docker_socket())
    container = get_containers(container_name)[0]

    print(f"Executing command in container '{container.name}': {cmd}")

    env = env or {}
    exec_handler = api_client.exec_create(
        container.name,
        cmd=f"bash -c {shlex.quote(cmd)}",
        environment=env,
        privileged=True,
        user=user,
    )

    output_generator = api_client.exec_start(exec_handler, stream=True)

    output = ""
    full_line = ""
    print("Command output:")
    for chunk in output_generator:
        chunk = chunk.decode()
        output += chunk
        chunk = chunk.split("\n", 1)
        if len(chunk) > 1:  # Indicates newline present
            full_line += chunk[0]
            print(strip_ansi(full_line), end="")
            full_line = ""
            if chunk[1]:
                full_line = chunk[1]
        else:
            full_line += chunk[0]
    if full_line:
        print(strip_ansi(full_line), end="")
    print("\n")

    exit_code = api_client.exec_inspect(exec_handler["Id"]).get("ExitCode")
    return CommandResult(cmd, output, exit_code)
