#!/usr/bin/env python3

import os
import docker
import sys
import subprocess
import shlex
import click

from time import sleep, gmtime, strftime
from pathlib import Path

from minitrino.settings import RESOURCE_LABEL

# Path references
# -----------------------------------------------------------------------------------
USER_HOME_DIR = os.path.expanduser("~")
MINITRINO_USER_DIR = os.path.abspath(os.path.join(USER_HOME_DIR, ".minitrino"))
CONFIG_FILE = os.path.abspath(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg"))
MINITRINO_LIB_DIR = os.path.join(
    Path(os.path.abspath(__file__)).resolve().parents[2], "lib"
)
SNAPSHOT_DIR = os.path.join(MINITRINO_LIB_DIR, "snapshots")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "test.tar.gz")
MINITRINO_USER_SNAPSHOTS_DIR = os.path.join(MINITRINO_USER_DIR, "snapshots")
# -----------------------------------------------------------------------------------


def log_success(msg):
    """Logs test status message to stdout."""

    click.echo(
        click.style(
            f"[{strftime('%d/%m/%Y %H:%M:%S', gmtime())} GMT] [SUCCESS] ",
            fg="green",
            bold=True,
        )
        + msg
        + "\n"
    )


def log_status(msg):
    """Logs test status message to stdout."""

    click.echo(
        click.style(
            f"[{strftime('%d/%m/%Y %H:%M:%S', gmtime())} GMT] [RUNNING] ",
            fg="yellow",
            bold=True,
        )
        + msg
        + "\n"
    )


def start_docker_daemon():
    """Starts the Docker daemon (works on MacOS/Ubuntu)."""

    if sys.platform.lower() == "darwin":
        exit_code = subprocess.call("open --background -a Docker", shell=True)
    elif "linux" in sys.platform.lower():
        exit_code = subprocess.call("sudo service docker start", shell=True)
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
        except:
            counter += 1
            sleep(1)


def stop_docker_daemon():
    """Stops the Docker daemon (works on MacOS/Ubuntu)."""

    if sys.platform.lower() == "darwin":
        exit_code = subprocess.call("osascript -e 'quit app \"Docker\"'", shell=True)
    elif "linux" in sys.platform.lower():
        exit_code = subprocess.call(
            "sudo service docker stop; sudo systemctl stop docker.socket", shell=True
        )
    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")
    if exit_code != 0:
        raise RuntimeError("Failed to stop Docker daemon.")

    # Hard wait for daemon to stop
    sleep(3)


def execute_command(cmd="", container=None, env={}):
    """Executes a command in the user's shell or inside of a container.

    - `cmd`: The command to execute.
    - `container`: Container name to execute command inside of.
    - `env`: Environment variables to pass to the container.

    Returns:

    ```python
    {
        "command": "str",
        "output": "str",
        "exit_code": int
    }
    ```"""

    if container:
        return _execute_in_container(cmd, container, env)
    else:
        return _execute_in_shell(cmd, env)


def _execute_in_shell(cmd="", env={}):
    """Executes a command in the host shell."""

    print(f"Executing command on host shell: {cmd}")

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
    with process as p:
        for line in p.stdout:
            output += line
            print(line, end="")  # process line here

    return {
        "command": cmd,
        "output": output,
        "exit_code": process.returncode,
    }


def _execute_in_container(cmd="", container_name="", env={}):
    """Executes a command inside of a container through the Docker SDK
    (similar to `docker exec`)."""

    docker_url = os.environ.get("DOCKER_HOST", "")
    api_client = docker.APIClient(base_url=docker_url)

    container = get_container(container_name)

    print(f"Executing command in container '{container.name}': {cmd}")

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

    return {"command": cmd, "output": output, "exit_code": exit_code}


def get_container(container_name=""):
    """Fetches running container by container name."""

    docker_url = os.environ.get("DOCKER_HOST", "")
    docker_client = docker.DockerClient(base_url=docker_url)
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    for c in containers:
        if c.name == container_name:
            return c
