#!/usr/bin/env python3

import os
import docker

import common
from minitrino.settings import RESOURCE_LABEL


def cleanup(remove_images=False):
    """Removes running Minitrino environments and deletes volumes. If specified,
    also removes images."""

    common.execute_command("minitrino -v down --sig-kill")
    common.execute_command("minitrino -v remove --volumes")

    if remove_images:
        print("Removing images...")
        common.execute_command(
            'docker images -q | grep -v "$(docker images minitrino/cluster -q)" | xargs -r docker rmi'
        )

    print("Disk space usage:")
    common.execute_command("df -h")


def dump_container_logs():
    """Dumps all container logs to stdout when an exception is raised."""

    docker_url = os.environ.get("DOCKER_HOST", "")
    docker_client = docker.DockerClient(base_url=docker_url)
    containers = docker_client.containers.list(
        all=True, filters={"label": RESOURCE_LABEL}
    )

    for container in containers:
        print(f"Dumping logs for container {container.name}:")
        logs = container.logs().decode("utf-8")  # Decode binary logs to string
        print(logs)
        print("\n")
