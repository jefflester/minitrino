#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import pathlib
import subprocess
import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast

SNAPSHOT_TEST_YAML_FILE = os.path.join(
    helpers.MINIPRESTO_USER_SNAPSHOTS_DIR,
    "test",
    "lib",
    "modules",
    "catalog",
    "test",
    "test.yml",
)


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    test_snapshot_no_directory()
    test_snapshot_active_env()
    test_snapshot_inactive_env()
    test_force()
    test_scrub()
    test_no_scrub()


def test_snapshot_no_directory():
    """
    Verifies that a snapshot can be created when there is no existing snapshots
    directory in the minipresto user home directory.
    """

    cleanup()
    subprocess.call(f"rm -rf {helpers.MINIPRESTO_USER_SNAPSHOTS_DIR}", shell=True)
    result = helpers.initialize_test(
        ["snapshot", "--name", "test", "--catalog", "test"]
    )

    run_assertions(result)

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_snapshot_active_env():
    """
    Verifies that a snapshot can be successfully created from an active
    environment.
    """

    cleanup()
    helpers.execute_command(["provision"])
    result = helpers.initialize_test(["snapshot", "--name", "test"])

    run_assertions(result, False)
    assert "Creating snapshot of active environment" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_snapshot_inactive_env():
    """
    Verifies that a snapshot can be successfully created from an inactive
    environment.
    """

    cleanup()
    result = helpers.initialize_test(
        ["snapshot", "--name", "test", "--catalog", "test"]
    )

    run_assertions(result)
    assert "Creating snapshot of inactive environment" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_force():
    """
    Verifies that the user can override the check to see if the resulting
    tarball exists.
    """

    result = helpers.initialize_test(
        ["snapshot", "--name", "test", "--catalog", "test", "--force"]
    )

    run_assertions(result)
    assert "Creating snapshot of inactive environment" in result.output

    cleanup()
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_no_scrub():
    """
    Verifies that the user config file is retained in full when scrubbing is
    disabled.
    """

    helpers.make_sample_config()
    result = helpers.initialize_test(
        ["snapshot", "--name", "test", "--catalog", "test", "--no-scrub"], "y\n"
    )

    run_assertions(result)
    with open(helpers.SNAPSHOT_CONFIG_FILE) as f:
        assert "*" * 20 not in f.read()

    cleanup()
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_scrub():
    """
    Verifies that sensitive data in user config file is scrubbed when scrubbing
    is enabled.
    """

    helpers.make_sample_config()
    result = helpers.initialize_test(
        ["snapshot", "--name", "test", "--catalog", "test"]
    )

    run_assertions(result)
    with open(helpers.SNAPSHOT_CONFIG_FILE) as f:
        assert "*" * 20 in f.read()

    cleanup()
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def run_assertions(result, check_yaml=True):
    """Runs standard assertions for the snapshot command."""

    if check_yaml:
        assert os.path.isfile(
            SNAPSHOT_TEST_YAML_FILE
        ), f"Not a valid file: {SNAPSHOT_TEST_YAML_FILE}"

    assert "Snapshot complete" in result.output
    assert result.exit_code == 0
    assert os.path.isfile(helpers.SNAPSHOT_CONFIG_FILE)

    command_snapshot_file = os.path.join(
        helpers.MINIPRESTO_USER_SNAPSHOTS_DIR, "test", "provision-snapshot.sh"
    )
    assert os.path.isfile(command_snapshot_file)

    with open(command_snapshot_file) as f:
        assert "minipresto -v --lib-path" in f.read()


def cleanup():
    """
    Removes test snapshot tarball and turns off running resources.
    """

    subprocess.call(f"rm -rf {helpers.SNAPSHOT_FILE}", shell=True)
    helpers.execute_command(["down"])


if __name__ == "__main__":
    main()
