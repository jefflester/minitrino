#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import docker

import src.common as common
import src.cli.helpers as helpers
from minitrino.settings import RESOURCE_LABEL

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    common.log_status(__file__)
    common.start_docker_daemon()
    cleanup()
    test_no_containers()
    test_running_containers()
    test_keep()


def test_no_containers():
    """Verifies that the down command functions appropriately when no containers
    are running."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "down"])

    assert result.exit_code == 0
    assert "No containers to bring down" in result.output

    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    assert len(containers) == 0, "There should be no running containers"

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_running_containers():
    """Verifies that the down command works when multiple containers are
    running. This also verifies the --sig-kill option works."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.execute_command(["-v", "provision", "--module", "test"])
    result = helpers.execute_command(["-v", "down", "--sig-kill"])

    assert result.exit_code == 0
    assert all(
        (
            "Stopped container" in result.output,
            "Removed container" in result.output,
            "test" in result.output,
            "trino" in result.output,
        )
    )

    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    assert len(containers) == 0, "There should be no running containers"

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_keep():
    """Verifies that the `--keep` flag works as expected."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.execute_command(["-v", "provision", "--module", "test"])
    result = helpers.execute_command(["-v", "down", "--keep"])

    assert "Stopped container" in result.output
    assert "Removed container" not in result.output

    docker_client = docker.from_env()
    containers = docker_client.containers.list(
        filters={"label": RESOURCE_LABEL}, all=True
    )

    for container in containers:
        assert container.name.lower() == "trino" or container.name.lower() == "test"

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def cleanup():
    """Stops/removes containers."""

    helpers.execute_command(["-v", "down", "--sig-kill"])


if __name__ == "__main__":
    main()
