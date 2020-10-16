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


def snapshot_test_yaml_file(snapshot_name="test"):
    return os.path.join(
        helpers.MINIPRESTO_USER_SNAPSHOTS_DIR,
        snapshot_name,
        "lib",
        "modules",
        "catalog",
        "test",
        "test.yml",
    )


def snapshot_config_file(snapshot_name="test"):
    return os.path.join(
        helpers.MINIPRESTO_USER_SNAPSHOTS_DIR, snapshot_name, "minipresto.cfg"
    )


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    test_snapshot_no_directory()
    test_snapshot_active_env()
    test_snapshot_inactive_env()
    test_valid_name()
    test_invalid_name()
    test_specific_directory()
    test_specific_directory_invalid()
    test_command_snapshot_file()
    test_force()
    test_scrub()
    test_no_scrub()


def test_snapshot_no_directory():
    """Verifies that a snapshot can be created when there is no existing
    snapshots directory in the Minipresto user home directory."""

    cleanup()
    subprocess.call(f"rm -rf {helpers.MINIPRESTO_USER_SNAPSHOTS_DIR}", shell=True)
    result = helpers.execute_command(
        ["-v", "snapshot", "--name", "test", "--module", "test"],
        command_input="y\n",
    )

    run_assertions(result)

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_snapshot_active_env():
    """Verifies that a snapshot can be successfully created from an active
    environment."""

    cleanup()
    helpers.execute_command(["provision"])
    result = helpers.execute_command(
        ["-v", "snapshot", "--name", "test"],
        command_input="y\n",
    )

    run_assertions(result, False)
    assert "Creating snapshot of active environment" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_snapshot_inactive_env():
    """Verifies that a snapshot can be successfully created from an inactive
    environment."""

    cleanup()
    result = helpers.execute_command(
        ["-v", "snapshot", "--name", "test", "--module", "test"],
        command_input="y\n",
    )

    run_assertions(result)
    assert "Creating snapshot of inactive environment" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_valid_name():
    """Tests that all valid characters can be present and succeed for a given
    snapshot name."""

    cleanup()
    result = helpers.execute_command(
        ["-v", "snapshot", "--name", "my-test_123", "--module", "test"],
        command_input="y\n",
    )

    run_assertions(result, snapshot_name="my-test_123")
    assert "Creating snapshot of inactive environment" in result.output

    cleanup(snapshot_name="my-test_123")

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_invalid_name():
    """Tests that all valid characters can be present and succeed for a given
    snapshot name."""

    cleanup()
    result = helpers.execute_command(
        ["-v", "snapshot", "--name", "##.my-test?", "--module", "test"],
        command_input="y\n",
    )

    assert result.exit_code == 1
    assert "Illegal character found in provided filename" in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_specific_directory():
    """Tests that the snapshot file can be saved in a user-specified
    directory."""

    cleanup()
    result = helpers.execute_command(
        [
            "-v",
            "snapshot",
            "--name",
            "test",
            "--module",
            "test",
            "--directory",
            "/tmp/",
        ],
        command_input="y\n",
    )

    run_assertions(result, True, check_path=os.path.join(os.sep, "tmp"))
    assert "Creating snapshot of inactive environment" in result.output

    subprocess.call("rm -rf /tmp/test.tar.gz", shell=True)

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_specific_directory_invalid():
    """Tests that the snapshot file cannot be saved in an invalid directory."""

    cleanup()
    result = helpers.execute_command(
        [
            "-v",
            "snapshot",
            "--name",
            "test",
            "--module",
            "test",
            "--directory",
            "/tmppp/",
        ],
        command_input="y\n",
    )

    assert "Cannot save snapshot in nonexistent directory:" in result.output
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_command_snapshot_file():
    """Verifies that an environment can be provisioned from a snapshot command
    file (these are written when a snapshot is created so that other users can
    easily reproduce the environment)."""

    command_snapshot_file = os.path.join(
        helpers.MINIPRESTO_USER_SNAPSHOTS_DIR, "test", "provision-snapshot.sh"
    )
    process = subprocess.Popen(
        command_snapshot_file,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    stdout, _ = process.communicate()

    assert process.returncode == 0
    assert "Environment provisioning complete" in stdout

    cleanup()
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_force():
    """Verifies that the user can override the check to see if the resulting
    tarball exists."""

    result = helpers.execute_command(
        ["-v", "snapshot", "--name", "test", "--module", "test", "--force"],
        command_input="y\n",
    )

    run_assertions(result)
    assert "Creating snapshot of inactive environment" in result.output

    cleanup()
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_no_scrub():
    """Verifies that the user config file is retained in full when scrubbing is
    disabled."""

    helpers.make_sample_config()
    result = helpers.execute_command(
        ["-v", "snapshot", "--name", "test", "--module", "test", "--no-scrub"],
        True,
        command_input="y\n",
    )

    run_assertions(result)
    with open(snapshot_config_file()) as f:
        assert "*" * 20 not in f.read()

    cleanup()
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_scrub():
    """Verifies that sensitive data in user config file is scrubbed when
    scrubbing is enabled."""

    helpers.make_sample_config()
    result = helpers.execute_command(
        ["-v", "snapshot", "--name", "test", "--module", "test"], command_input="y\n"
    )

    run_assertions(result)
    with open(snapshot_config_file()) as f:
        assert "*" * 20 in f.read()

    cleanup()
    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def run_assertions(
    result, check_yaml=True, snapshot_name="test", check_path=helpers.SNAPSHOT_DIR
):
    """Runs standard assertions for the snapshot command."""

    if check_yaml:
        assert os.path.isfile(
            snapshot_test_yaml_file(snapshot_name)
        ), f"Not a valid file: {snapshot_test_yaml_file(snapshot_name)}"

    assert "Snapshot complete" in result.output
    assert result.exit_code == 0
    if os.path.isfile(os.path.join(helpers.MINIPRESTO_USER_DIR, "minipresto.cfg")):
        assert os.path.isfile(snapshot_config_file(snapshot_name))

    command_snapshot_file = os.path.join(
        helpers.MINIPRESTO_USER_SNAPSHOTS_DIR, snapshot_name, "provision-snapshot.sh"
    )
    assert os.path.isfile(command_snapshot_file)

    # Check that snapshot tarball exists
    assert os.path.isfile(os.path.join(check_path, f"{snapshot_name}.tar.gz"))

    with open(command_snapshot_file) as f:
        assert "minipresto -v --lib-path" in f.read()


def cleanup(snapshot_name="test"):
    """Removes test snapshot tarball and turns off running resources."""

    if not snapshot_name == "test":
        subprocess.call(
            f"rm -rf {os.path.join(helpers.MINIPRESTO_USER_SNAPSHOTS_DIR, snapshot_name)}.tar.gz",
            shell=True,
        )
    else:
        subprocess.call(f"rm -rf {helpers.SNAPSHOT_FILE}", shell=True)

    helpers.execute_command(["down", "--sig-kill"])


if __name__ == "__main__":
    main()
