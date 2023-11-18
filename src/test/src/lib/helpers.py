#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import subprocess

from minitrino.settings import RESOURCE_LABEL


def execute_command(cmd="", container=None, env={}):
    """Executes a command in the user's shell or inside of a container.

    - `cmd`: The command to execute.
    - `container`: Container name to execute command inside of.
    - `env`: Environment variables to pass to the container.

    Returns command, output, and return code in a dict."""

    if container:
        return execute_in_container(cmd, container, env)
    else:
        return execute_in_shell(cmd)


def execute_in_shell(cmd=""):
    """Executes a command in the host shell."""

    print(f"Executing command on host shell: {cmd}")

    process = subprocess.Popen(
        cmd,
        shell=True,
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
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
        "return_code": process.returncode,
    }


def execute_in_container(cmd="", container_name="", env={}):
    """Executes a command inside of a container through the Docker SDK
    (similar to `docker exec`)."""

    docker_url = os.environ.get("DOCKER_HOST", "")
    api_client = docker.APIClient(base_url=docker_url)

    container = get_container(container_name)

    print(f"Executing command in container '{container.name}': {cmd}")

    exec_handler = api_client.exec_create(
        container.name, cmd=cmd, privileged=True, tty=True, environment=env
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

    return_code = api_client.exec_inspect(exec_handler["Id"]).get("ExitCode")

    return {"command": cmd, "output": output, "return_code": return_code}


def get_container(container_name=""):
    """Fetches running container by container name."""

    docker_url = os.environ.get("DOCKER_HOST", "")
    docker_client = docker.DockerClient(base_url=docker_url)
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    for c in containers:
        if c.name == container_name:
            return c


def cleanup():
    "Removes running Minitrino environments and deletes volumes."

    execute_command("minitrino -v down --sig-kill")
    execute_command("minitrino -v remove --volumes")
