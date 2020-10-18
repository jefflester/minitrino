#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# TODO: Test docker host
# TODO: Test symlink paths
# TODO: Test invalid/nonexistant library path

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
        ["-v", "modules", "--running"],
    )
    test_env()
    test_multiple_env()
    test_invalid_env()


def test_daemon_off_all(*args):
    """Verifies that each Minipresto command properly exits properly if the
    Docker daemon is off or unresponsive."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

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

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "--env", "COMPOSE_PROJECT_NAME=test", "version"]
    )

    assert result.exit_code == 0
    assert "COMPOSE_PROJECT_NAME" and "test" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_multiple_env():
    """Verifies that multiple environment variables can be successfully passed
    in."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        [
            "-v",
            "--env",
            "COMPOSE_PROJECT_NAME=test",
            "--env",
            "STARBURST_VER=338-e.1",
            "--env",
            "PRESTO=is=awesome",
            "version",
        ]
    )

    assert result.exit_code == 0
    assert all(
        (
            '"COMPOSE_PROJECT_NAME": "test"' in result.output,
            '"STARBURST_VER": "338-e.1"' in result.output,
            '"PRESTO": "is=awesome"' in result.output,
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_invalid_env():
    """Verifies that an invalid environment variable will cause the CLI to exit
    with a non-zero status code."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "--env", "COMPOSE_PROJECT_NAMEtest", "version"]
    )

    assert result.exit_code == 2
    assert "Invalid key-value pair" in result.output

    result = helpers.execute_command(["-v", "--env", "=", "version"])

    assert result.exit_code == 2
    assert "Invalid key-value pair" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
