#!/usr/bin/env python3

import docker

import src.common as common
import src.cli.utils as utils
from minitrino.settings import RESOURCE_LABEL

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    common.log_status(__file__)
    common.start_docker_daemon()
    cleanup()
    test_coordinator_only()
    test_workers()


def test_coordinator_only():
    """Verifies that the restart command works when only the coordinator is
    running."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    utils.execute_cli_cmd(["-v", "provision"])
    result = utils.execute_cli_cmd(["-v", "restart"])

    assert result.exit_code == 0
    assert "'minitrino' restarted successfully" in result.output
    assert check_containers() == 0, "There should be no running containers"

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_workers():
    """Verifies that the restart command works when a coordinator and workers
    are running."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    utils.execute_cli_cmd(["-v", "provision", "--workers", "2"])
    result = utils.execute_cli_cmd(["-v", "restart"])

    assert result.exit_code == 0
    assert "'minitrino' restarted successfully" in result.output
    assert "'minitrino-worker-2' restarted successfully." in result.output
    assert check_containers() == 0, "There should be no running containers"

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def check_containers():
    """Checks for running Minitrino containers."""

    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    return len(containers)


def cleanup():
    """Stops/removes containers."""

    utils.execute_cli_cmd(["-v", "down", "--sig-kill"])


if __name__ == "__main__":
    main()
