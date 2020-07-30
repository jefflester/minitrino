#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import minipresto.test.helpers as helpers

from click.testing import CliRunner
from minipresto.cli import cli

from minipresto.settings import RESOURCE_LABEL


def main():
    helpers.log_status("Running test_provision")
    test_daemon_off()
    test_standalone()
    test_invalid_catalog_module()
    test_invalid_security_module()
    test_env_override()
    test_invalid_env_override()
    test_build()


def test_daemon_off():
    """
    Verifies the command exits properly if the Docker daemon is off or
    unresponsive.
    """

    helpers.stop_docker_daemon()

    runner = CliRunner()
    result = runner.invoke(cli, ["provision"])
    assert result.exit_code == 1
    assert (
        "Error when pinging the Docker server. Is the Docker daemon running?"
        in result.output
    )

    helpers.log_status(f"Passed test_daemon_off")


def test_standalone():
    """
    Verifies that a standalone Presto container is provisioned when no options 
    are passed in.
    """

    helpers.start_docker_daemon()

    runner = CliRunner()
    result = runner.invoke(cli, ["provision"])
    assert result.exit_code == 0
    assert "Provisioning standalone Presto container" in result.output

    containers = get_containers()
    assert len(containers) == 1

    for container in containers:
        assert container.name == "presto"

    helpers.log_status(f"Passed test_standalone")
    cleanup(runner)


def test_invalid_catalog_module():
    """
    Verifies that a non-zero status code is returned when attempting to 
    provision an invalid catalog module.
    """

    runner = CliRunner()
    result = runner.invoke(
        cli, ["provision", "--catalog", "hive-hms", "not-a-real-module"]
    )
    assert result.exit_code == 1
    assert "Invalid catalog module" in result.output

    containers = get_containers()
    assert len(containers) == 0

    helpers.log_status(f"Passed test_invalid_catalog_module")
    cleanup(runner)


def test_invalid_security_module():
    """
    Verifies that a non-zero status code is returned when attempting to 
    provision an invalid security module.
    """

    runner = CliRunner()
    result = runner.invoke(
        cli, ["provision", "--security", "ldap", "not-a-real-module"]
    )
    assert result.exit_code == 1
    assert "Invalid security module" in result.output

    containers = get_containers()
    assert len(containers) == 0

    helpers.log_status(f"Passed test_invalid_security_module")
    cleanup(runner)


def test_env_override():
    """
    Verifies that an overridden environment variable can be successfully
    passed in.
    """

    runner = CliRunner()
    result = runner.invoke(
        cli, ["-v", "provision", "--env", "COMPOSE_PROJECT_NAME=test"]
    )
    assert result.exit_code == 0
    assert "COMPOSE_PROJECT_NAME=test" in result.output

    containers = get_containers()
    assert len(containers) == 1

    for container in containers:
        assert container.name == "presto"

    helpers.log_status(f"Passed test_env_override")
    cleanup(runner)


def test_invalid_env_override():
    """
    Verifies that an invalid, overridden environment variable will cause
    the CLI to exit with a non-zero status code.
    """

    runner = CliRunner()
    result = runner.invoke(
        cli, ["-v", "provision", "--env", "COMPOSE_PROJECT_NAME===test"]
    )
    assert result.exit_code == 1
    assert "Invalid environment variable" in result.output

    containers = get_containers()
    assert len(containers) == 0

    helpers.log_status(f"Passed test_invalid_env_override")
    cleanup(runner)


def test_build():
    """
    Verifies that we can successfully build from a given module's
    Docker build context.
    """

    runner = CliRunner()
    result = runner.invoke(
        cli, ["-v", "provision", "--catalog", "test", "elasticsearch", "-d", "--build"]
    )
    assert result.exit_code == 0
    assert all(
        (
            "Environment provisioning complete" in result.output,
            "Received native Docker Compose options" in result.output,
        )
    )

    containers = get_containers()
    assert len(containers) == 3

    helpers.log_status(f"Passed test_build")
    cleanup(runner)


def get_containers():
    """Returns all running minipresto containers."""

    docker_client = docker.from_env()
    return docker_client.containers.list(filters={"label": RESOURCE_LABEL})


def cleanup(runner):
    """
    Brings down containers and removes resources.
    """

    runner.invoke(cli, ["down"])


if __name__ == "__main__":
    main()
