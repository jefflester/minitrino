"""Common utilities for Minitrino integration and system tests.

This module provides helper functions and classes for managing Docker containers,
executing shell commands, and handling test environment setup and teardown.
"""

import os
import sys
import shlex
import docker
import subprocess

from time import sleep
from pathlib import Path
from dataclasses import dataclass
from docker.models.containers import Container
from typing import Optional

from minitrino.settings import ROOT_LABEL


USER_HOME_DIR = os.path.expanduser("~")
MINITRINO_USER_DIR = os.path.abspath(os.path.join(USER_HOME_DIR, ".minitrino"))
CONFIG_FILE = os.path.abspath(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg"))
MINITRINO_LIB_DIR = os.path.join(
    Path(os.path.abspath(__file__)).resolve().parents[2], "lib"
)
SNAPSHOT_DIR = os.path.join(MINITRINO_LIB_DIR, "snapshots")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "test.tar.gz")
MINITRINO_USER_SNAPSHOTS_DIR = os.path.join(MINITRINO_USER_DIR, "snapshots")


def start_docker_daemon() -> None:
    """
    Start the Docker daemon.

    Raises
    ------
    RuntimeError
        If the Docker daemon fails to start or the platform is incompatible.
    TimeoutError
        If the Docker daemon does not start within one minute.

    Notes
    -----
    This function starts the Docker daemon on MacOS and Ubuntu platforms. It raises a
    RuntimeError if the daemon fails to start or the platform is incompatible. It also
    raises a TimeoutError if the daemon does not start within one minute.
    """
    if sys.platform.lower() == "darwin":
        exit_code = execute_cmd("open --background -a Docker").exit_code
    elif "linux" in sys.platform.lower():
        exit_code = execute_cmd("sudo service docker start").exit_code
    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")
    if exit_code != 0:
        raise RuntimeError("Failed to start Docker daemon.")

    counter = 0
    while counter <= 61:
        if counter == 61:
            raise TimeoutError("Docker daemon failed to start after one minute.")
        try:
            docker_client = docker.from_env()
            docker_client.ping()
            break
        except Exception:
            counter += 1
            sleep(1)


def stop_docker_daemon() -> None:
    """
    Stop the Docker daemon.

    Raises
    ------
    RuntimeError
        If the Docker daemon fails to stop or the platform is incompatible.

    Notes
    -----
    This function stops the Docker daemon on MacOS and Ubuntu platforms. It raises a
    RuntimeError if the daemon fails to stop or the platform is incompatible.
    """
    if sys.platform.lower() == "darwin":
        exit_code = execute_cmd("osascript -e 'quit app \"Docker\"'").exit_code
    elif "linux" in sys.platform.lower():
        exit_code = execute_cmd(
            "sudo service docker stop; sudo systemctl stop docker.socket"
        ).exit_code
    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")
    if exit_code != 0:
        raise RuntimeError("Failed to stop Docker daemon.")

    # Hard wait for daemon to stop
    sleep(3)


def get_containers(container_name: str = "", all: bool = False) -> list[Container]:
    """
    Fetch Minitrino containers.

    If a name is provided, return the container with the specified name. If no name is
    provided, return all containers.

    Parameters
    ----------
    container_name : str
        Name of the container to fetch.
    all : bool
        Whether to fetch all containers or only running containers.

    Returns
    -------
    list[Container]
        List of containers if `container_name` is not provided, otherwise the container
        with the specified name.

    Raises
    ------
    RuntimeError
        If the container is not found.
    """
    docker_url = os.environ.get("DOCKER_HOST", "")
    docker_client = docker.DockerClient(base_url=docker_url)
    containers: list[Container] = docker_client.containers.list(
        filters={"label": ROOT_LABEL}, all=all
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
    cmd: str = "", container: Optional[str] = None, env: Optional[dict[str, str]] = None
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

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit code.
    """
    env = env or {}
    if container:
        return _execute_in_container(cmd, container, env)
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
        Command result object containing the command output and exit code.
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
    return CommandResult(cmd, output, process.returncode)


def _execute_in_container(
    cmd: str = "", container_name: str = "", env: Optional[dict[str, str]] = None
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

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit code.
    """
    docker_url = os.environ.get("DOCKER_HOST", "")
    api_client = docker.APIClient(base_url=docker_url)

    container = get_containers(container_name)[0]

    print(f"Executing command in container '{container.name}': {cmd}")

    env = env or {}
    exec_handler = api_client.exec_create(
        container.name,
        cmd=f"bash -c {shlex.quote(cmd)}",
        privileged=True,
        tty=True,
        environment=env,
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
