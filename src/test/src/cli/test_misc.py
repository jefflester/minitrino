#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import src.common as common
import src.cli.utils as utils

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    common.log_status(__file__)
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
    test_invalid_lib()


def test_daemon_off_all(*args):
    """Verifies that each Minitrino command properly exits properly if the
    Docker daemon is off or unresponsive."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    def run_daemon_assertions(result):
        """Runs standard assertions."""

        assert result.exit_code == 2, f"Invalid exit code: {result.exit_code}"
        assert (
            "Error when pinging the Docker server. Is the Docker daemon running?"
            in result.output
        ), f"Unexpected output: {result.output}"

    common.stop_docker_daemon()

    for arg in args:
        if "snapshot" in arg:
            result = utils.execute_cli_cmd(arg, command_input="y\n")
        else:
            result = utils.execute_cli_cmd(arg)
        run_daemon_assertions(result)

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_env():
    """Verifies that an environment variable can be successfully passed in."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    # User environment variable
    result = utils.execute_cli_cmd(
        ["-v", "--env", "COMPOSE_PROJECT_NAME=test", "version"]
    )

    assert result.exit_code == 0
    assert "COMPOSE_PROJECT_NAME" and "test" in result.output

    # Shell environment variable
    result = utils.execute_cli_cmd(
        ["-v", "version"],
        env={"COMPOSE_PROJECT_NAME": "test"},
    )

    assert result.exit_code == 0
    assert "COMPOSE_PROJECT_NAME" and "test" in result.output

    # Config environment variable
    utils.make_sample_config()
    cmd = (
        f'bash -c "cat << EOF >> {common.CONFIG_FILE}\n'
        f"COMPOSE_PROJECT_NAME=test\n"
        f'EOF"'
    )
    common.execute_command(cmd)

    result = utils.execute_cli_cmd(
        ["-v", "version"],
    )

    assert result.exit_code == 0
    assert "COMPOSE_PROJECT_NAME" and "test" in result.output

    common.execute_command(f'bash -c "rm {common.CONFIG_FILE}\n"')

    result = utils.execute_cli_cmd(
        ["-v", "version"],
    )

    assert result.exit_code == 0
    assert "COMPOSE_PROJECT_NAME" and "minitrino" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_multiple_env():
    """Verifies that multiple environment variables can be successfully passed
    in."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(
        [
            "-v",
            "--env",
            "COMPOSE_PROJECT_NAME=test",
            "--env",
            "CLUSTER_VER=388-e",
            "--env",
            "TRINO=is=awesome",
            "version",
        ]
    )

    assert result.exit_code == 0
    assert all(
        (
            '"COMPOSE_PROJECT_NAME": "test"' in result.output,
            '"CLUSTER_VER": "388-e"' in result.output,
            '"TRINO": "is=awesome"' in result.output,
        )
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_invalid_env():
    """Verifies that an invalid environment variable will cause the CLI to exit
    with a non-zero status code."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(
        ["-v", "--env", "COMPOSE_PROJECT_NAMEtest", "version"]
    )

    assert result.exit_code == 2
    assert "Invalid key-value pair" in result.output

    result = utils.execute_cli_cmd(["-v", "--env", "=", "version"])

    assert result.exit_code == 2
    assert "Invalid key-value pair" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_invalid_lib():
    """Verifies that Minitrino exists with a user error if pointing to an
    invalid library."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    # Real directory, but ain't a real library
    result = utils.execute_cli_cmd(["-v", "--env", "LIB_PATH=/tmp/", "modules"])

    assert result.exit_code == 2
    assert "This operation requires a library to be installed" in result.output

    # Fake directory
    result = utils.execute_cli_cmd(
        ["-v", "--env", "LIB_PATH=/gucci-is-overrated/", "modules"]
    )

    assert result.exit_code == 2
    assert "This operation requires a library to be installed" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


if __name__ == "__main__":
    main()
