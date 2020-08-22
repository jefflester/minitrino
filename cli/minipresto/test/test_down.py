#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import docker
import minipresto.test.helpers as helpers

from click.testing import CliRunner
from minipresto.cli import cli

from minipresto.settings import RESOURCE_LABEL


def main():
    helpers.log_status("Running test_down")
    test_daemon_off()
    test_no_containers()
    test_running_containers()


def test_daemon_off():
    """
    Verifies the command exits properly if the Docker daemon is off or
    unresponsive.
    """

    helpers.stop_docker_daemon()

    runner = CliRunner()
    result = runner.invoke(cli, ["down"])
    assert result.exit_code == 1, result.output
    assert (
        "Error when pinging the Docker server. Is the Docker daemon running?"
        in result.output
    ), result.output

    helpers.log_status(f"Passed test_daemon_off")


def test_no_containers():
    """
    Verifies that the down command functions appropriately when no containers
    are running.
    """

    helpers.start_docker_daemon()

    runner = CliRunner()
    runner.invoke(cli, ["down"])  # Run preliminary down in case something is up
    result = runner.invoke(cli, ["down"])
    assert result.exit_code == 0, result.output
    assert "No containers to bring down" in result.output, result.output

    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    assert len(containers) == 0

    helpers.log_status(f"Passed test_no_containers")
    cleanup(runner)


def test_running_containers():
    """
    Verifies that the down command works when multiple containers are running.
    """

    runner = CliRunner()
    runner.invoke(cli, ["down"])  # Run preliminary down in case something is up
    runner.invoke(cli, ["provision", "--catalog", "test"])
    result = runner.invoke(cli, ["-v", "down"])
    assert result.exit_code == 0, result.output
    assert all(
        (
            "Stopped/removed container" in result.output,
            "test" in result.output,
            "presto" in result.output,
        )
    ), result.output

    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
    assert len(containers) == 0

    helpers.log_status(f"Passed test_running_containers")
    cleanup(runner)


def cleanup(runner):
    """
    Stops/removes containers.
    """

    runner.invoke(cli, ["down"])


if __name__ == "__main__":
    main()
