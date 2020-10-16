#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# TODO: Test docker host
# TODO: Test symlink paths

import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    helpers.log_status(__file__)
    test_daemon_off_all(
        ["-v", "down"],
        ["-v", "provision"],
        ["-v", "remove"],
        [
            "-v",
            "snapshot",
            "--name",
            "test",
        ],  # Applicable only when snapshotting active environment
    )
    test_env()
    test_multiple_env()
    test_invalid_env()


def test_daemon_off_all(*args):
    """Verifies that each Minipresto command properly exits properly if the
    Docker daemon is off or unresponsive."""

    def run_daemon_assertions(result):
        """Runs standard assertions."""

        assert result.exit_code == 2, f"Invalid exit code: {result.exit_code}"
        assert (
            "Error when pinging the Docker server. Is the Docker daemon running?"
            in result.output
        ), f"Unexpected output: {result.output}"

    helpers.stop_docker_daemon()

    for arg in args:
        result = helpers.execute_command(arg)
        run_daemon_assertions(result)

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_env():
    """Verifies that an environment variable can be successfully passed in."""

    result = helpers.execute_command(
        ["-v", "--env", "COMPOSE_PROJECT_NAME=test", "version"]
    )

    assert result.exit_code == 0
    assert "COMPOSE_PROJECT_NAME" and "test" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_multiple_env():
    """Verifies that multiple environment variables can be successfully passed
    in."""

    result = helpers.execute_command(
        [
            "-v",
            "--env",
            "COMPOSE_PROJECT_NAME=test",
            "--env",
            "STARBURST_VER=338-e.1",
            "--env",
            "PRESTO=is_awesome",
            "version",
        ]
    )

    assert result.exit_code == 0
    assert all(
        (
            '"COMPOSE_PROJECT_NAME": "test"' in result.output,
            '"STARBURST_VER": "338-e.1"' in result.output,
            '"PRESTO": "is_awesome"' in result.output,
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_invalid_env():
    """Verifies that an invalid environment variable will cause the CLI to exit
    with a non-zero status code."""

    result = helpers.execute_command(
        ["-v", "--env", "COMPOSE_PROJECT_NAME===test", "version"]
    )

    assert result.exit_code == 2
    assert "Invalid environment variable" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_docker_host():
    """Validates you can connect to another Docker host."""


def test_symlink_paths():
    """Ensures Minipresto can find paths from symlinks."""


if __name__ == "__main__":
    main()
