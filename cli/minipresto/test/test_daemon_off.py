#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast
from click.testing import CliRunner
from minipresto.cli import cli


def main():
    helpers.log_status(__file__)
    helpers.stop_docker_daemon()
    test_daemon_off_all(
        ["-v", "down"],
        ["-v", "provision"],
        ["-v", "remove"],
        ["-v", "snapshot", "--name", "test"], # Applicable only when snapshotting active environment
    )


def test_daemon_off_all(*args):
    """
    Verifies that each Minipresto command properly exits properly if the Docker
    daemon is off or unresponsive.
    """

    for arg in args:
        result = helpers.execute_command(arg)
        run_assertions(result)

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def run_assertions(result):
    """Runs standard assertions."""

    assert result.exit_code == 1, f"Invalid exit code: {result.exit_code}"
    assert (
        "Error when pinging the Docker server. Is the Docker daemon running?"
        in result.output
    ), f"Unexpected output: {result.output}"


if __name__ == "__main__":
    main()
