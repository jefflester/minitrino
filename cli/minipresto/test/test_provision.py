#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import subprocess
import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast
from minipresto.settings import RESOURCE_LABEL


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    test_standalone()
    test_invalid_catalog_module()
    test_invalid_security_module()
    test_env_override()
    test_invalid_env_override()
    test_build_bootstrap_config_props()


def test_standalone():
    """
    Verifies that a standalone Presto container is provisioned when no options 
    are passed in.
    """

    result = helpers.initialize_test(["-v", "provision"])

    assert result.exit_code == 0
    assert "Provisioning standalone" in result.output

    containers = get_containers()
    assert len(containers) == 1

    for container in containers:
        assert container.name == "presto"

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_invalid_catalog_module():
    """
    Verifies that a non-zero status code is returned when attempting to 
    provision an invalid catalog module.
    """

    result = helpers.initialize_test(
        ["-v", "provision", "--catalog", "hive-hms", "not-a-real-module"]
    )

    assert result.exit_code == 1
    assert "Invalid catalog module" in result.output

    containers = get_containers()
    assert len(containers) == 0

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_invalid_security_module():
    """
    Verifies that a non-zero status code is returned when attempting to 
    provision an invalid security module.
    """

    result = helpers.initialize_test(
        ["-v", "provision", "--security", "ldap", "not-a-real-module"]
    )

    assert result.exit_code == 1
    assert "Invalid security module" in result.output

    containers = get_containers()
    assert len(containers) == 0

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_env_override():
    """
    Verifies that an overridden environment variable can be successfully
    passed in.
    """

    result = helpers.initialize_test(
        ["-v", "provision", "--env", "COMPOSE_PROJECT_NAME=test"]
    )

    assert result.exit_code == 0
    assert "COMPOSE_PROJECT_NAME=test" in result.output

    containers = get_containers()
    assert len(containers) == 1

    for container in containers:
        assert container.name == "presto"

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_invalid_env_override():
    """
    Verifies that an invalid, overridden environment variable will cause
    the CLI to exit with a non-zero status code.
    """

    result = helpers.initialize_test(
        ["-v", "provision", "--env", "COMPOSE_PROJECT_NAME===test"]
    )

    assert result.exit_code == 1
    assert "Invalid environment variable" in result.output

    containers = get_containers()
    assert len(containers) == 0

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_build_bootstrap_config_props():
    """
    Verifies (1) we can successfully build from a given module's Docker build
    context, (2) checks for successful bootstrap execution, and (3) checks for
    successful adding of config properties to Presto config.properties file.
    """

    result = helpers.initialize_test(
        ["-v", "provision", "--catalog", "test", "-d", "--build"]
    )

    assert result.exit_code == 0
    assert all(
        (
            "Environment provisioning complete" in result.output,
            "Received native Docker Compose options" in result.output,
            "Found duplicate property key in config.properties file" in result.output,
        )
    )

    containers = get_containers()
    assert len(containers) == 2

    process_config_props_check = subprocess.Popen(
        f"docker exec -i presto cat /usr/lib/presto/etc/config.properties",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    process_bootstrap_check = subprocess.Popen(
        f"docker exec -i test cat /root/test_bootstrap.txt",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    config_prop_output, _ = process_config_props_check.communicate()
    bootstrap_check_output, _ = process_bootstrap_check.communicate()

    assert all(
        (
            "query.max-stage-count=105" in str(config_prop_output),
            "query.max-execution-time=1h" in str(config_prop_output),
            "hello world" in str(bootstrap_check_output),
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def get_containers():
    """Returns all running minipresto containers."""

    docker_client = docker.from_env()
    return docker_client.containers.list(filters={"label": RESOURCE_LABEL})


def cleanup():
    """
    Brings down containers and removes resources.
    """

    helpers.execute_command(["down"])


if __name__ == "__main__":
    main()
