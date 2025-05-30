"""Common utilities for Minitrino integration and system tests.

This module provides helper functions and classes for managing Docker
containers, executing shell commands, and handling test environment
setup and teardown.
"""

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
from typing import Optional

import docker
from docker.models.containers import Container

from minitrino.core.docker.socket import resolve_docker_socket
from minitrino.settings import ROOT_LABEL

USER_HOME_DIR = os.path.expanduser("~")
MINITRINO_USER_DIR = os.path.abspath(os.path.join(USER_HOME_DIR, ".minitrino"))
CONFIG_FILE = os.path.abspath(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg"))
MINITRINO_LIB_DIR = os.path.join(
    Path(os.path.abspath(__file__)).resolve().parents[2], "lib"
)


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
        result = subprocess.run(
            cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0
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
                "No supported Docker backend found (Docker Desktop, OrbStack, Colima, Rancher Desktop)."
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

    for _ in range(61):
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
        result = subprocess.run(
            cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except Exception:
        return False


def stop_docker_daemon() -> None:
    """
    Stop the Docker daemon.

    Raises
    ------
    RuntimeError
        If no supported Docker backend is found or the platform is
        unsupported.
    TimeoutError
        If the Docker daemon does not stop within one minute.
    """
    stopped = False
    if sys.platform.lower() == "darwin":
        if shutil.which("osascript"):
            stopped = try_stop(["osascript", "-e", 'quit app "Docker"'])
        if not stopped and shutil.which("osascript"):
            stopped = try_stop(["osascript", "-e", 'quit app "OrbStack"'])
        if not stopped and shutil.which("colima"):
            stopped = try_stop(["colima", "stop"])
        if not stopped and shutil.which("osascript"):
            stopped = try_stop(["osascript", "-e", 'quit app "Rancher Desktop"'])
        if not stopped:
            raise RuntimeError(
                "No supported Docker backend found "
                "(Docker Desktop, OrbStack, Colima, Rancher Desktop) for stopping."
            )
    elif "linux" in sys.platform.lower():
        if shutil.which("systemctl"):
            stopped = try_stop(["sudo", "systemctl", "stop", "docker"])
        if not stopped and shutil.which("service"):
            stopped = try_stop(["sudo", "service", "docker", "stop"])
        if not stopped:
            raise RuntimeError(
                "Could not stop Docker daemon (systemctl/service not available)."
            )
    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")

    # Wait for Docker to be unavailable
    for counter in range(61):
        if not is_docker_running():
            return
        sleep(1)
    raise TimeoutError("Docker daemon failed to stop after one minute.")


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
    user: Optional[str] = "root",
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
    user: Optional[str] = "root",
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
        tty=True,
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
            print(full_line, end="")
            full_line = ""
            if chunk[1]:
                full_line = chunk[1]
        else:
            full_line += chunk[0]

    if full_line:
        print(full_line, end="")

    exit_code = api_client.exec_inspect(exec_handler["Id"]).get("ExitCode")
    return CommandResult(cmd, output, exit_code)


def execute_in_coordinator(
    cmd: str = None, container_name: str = None
) -> CommandResult:
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
    return _execute_in_container(
        cmd=wrapped_cmd, container_name=container_name, user=uid
    )
