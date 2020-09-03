#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import docker
import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast
from minipresto.settings import RESOURCE_LABEL


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    test_no_containers()
    test_running_containers()


def test_no_containers():
    """
    Verifies that the down command functions appropriately when no containers
    are running.
    """

    # Run preliminary `down` in case a container is running
    helpers.execute_command(["-v", "down"])
    result = helpers.initialize_test(["-v", "down"])

    assert result.exit_code == 0
    assert "No containers to bring down" in result.output

    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    assert len(containers) == 0, "There should be no running containers"

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_running_containers():
    """
    Verifies that the down command works when multiple containers are running.
    """

    helpers.execute_command(["-v", "down"])
    helpers.execute_command(["-v", "provision", "--catalog", "test"])
    result = helpers.initialize_test(["-v", "down"])

    assert result.exit_code == 0
    assert all(
        (
            "Stopped/removed container" in result.output,
            "test" in result.output,
            "presto" in result.output,
        )
    )

    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    assert len(containers) == 0, "There should be no running containers"

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def cleanup():
    """
    Stops/removes containers.
    """

    helpers.execute_command(["-v", "down"])


if __name__ == "__main__":
    main()
