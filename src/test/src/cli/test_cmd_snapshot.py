#!/usr/bin/env python3

import os

import src.common as common
import src.cli.utils as utils

from inspect import currentframe
from types import FrameType
from typing import cast


def snapshot_test_yaml_file(snapshot_name="test"):
    return os.path.join(
        common.MINITRINO_USER_SNAPSHOTS_DIR,
        snapshot_name,
        "lib",
        "modules",
        "catalog",
        "test",
        "test.yaml",
    )


def snapshot_config_file(snapshot_name="test"):
    return os.path.join(
        common.MINITRINO_USER_SNAPSHOTS_DIR, snapshot_name, "minitrino.cfg"
    )


def main():
    common.log_status(__file__)
    common.start_docker_daemon()
    test_snapshot_no_directory()
    test_snapshot_standalone()
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
    snapshots directory in the Minitrino user home directory."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    common.execute_command(f"rm -rf {common.MINITRINO_USER_SNAPSHOTS_DIR}")
    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "test", "--module", "test"],
        command_input="y\n",
    )

    run_assertions(result)

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_snapshot_active_env():
    """Verifies that a snapshot can be successfully created from an active
    environment."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    utils.execute_cli_cmd(["-v", "provision", "--module", "test"])
    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "test"],
        command_input="y\n",
    )

    run_assertions(result, False)
    assert "Creating snapshot of active environment" in result.output

    # This also verifies we pick up on dependent modules that are provisioned
    # alongside another module
    command_snapshot_file = os.path.join(
        common.MINITRINO_USER_SNAPSHOTS_DIR, "test", "provision-snapshot.sh"
    )
    with open(command_snapshot_file, "r") as f:
        assert (
            "--module file-access-control" and "--module test" in f.read()
        ), "Expected modules not found in snapshot provisioning file"

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_snapshot_standalone():
    """Verifies that a the standalone cluster module can be snapshotted."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "test"],
        command_input="y\n",
    )

    run_assertions(result, False)
    assert "Snapshotting cluster resources only" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_snapshot_inactive_env():
    """Verifies that a snapshot can be successfully created from an inactive
    environment."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "test", "--module", "test"],
        command_input="y\n",
    )

    run_assertions(result)
    assert "Creating snapshot of specified modules" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_valid_name():
    """Tests that all valid characters can be present and succeed for a given
    snapshot name."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "my-test_123", "--module", "test"],
        command_input="y\n",
    )

    run_assertions(result, snapshot_name="my-test_123")
    assert "Creating snapshot of specified modules" in result.output

    cleanup(snapshot_name="my-test_123")

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_invalid_name():
    """Tests that all valid characters can be present and succeed for a given
    snapshot name."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "##.my-test?", "--module", "test"],
        command_input="y\n",
    )

    assert result.exit_code == 2
    assert "Illegal character found in provided filename" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_specific_directory():
    """Tests that the snapshot file can be saved in a user-specified
    directory."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    result = utils.execute_cli_cmd(
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
    assert "Creating snapshot of specified modules" in result.output

    common.execute_command("rm -rf /tmp/test.tar.gz")

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_specific_directory_invalid():
    """Tests that the snapshot file cannot be saved in an invalid directory."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    result = utils.execute_cli_cmd(
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
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_command_snapshot_file():
    """Verifies that an environment can be provisioned from a snapshot command
    file (these are written when a snapshot is created so that other users can
    easily reproduce the environment)."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    cleanup()
    utils.execute_cli_cmd(["-v", "provision", "--module", "test"])
    utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "test"],
        command_input="y\n",
    )
    utils.execute_cli_cmd(["down", "--sig-kill"])

    command_snapshot_file = os.path.join(
        common.MINITRINO_USER_SNAPSHOTS_DIR, "test", "provision-snapshot.sh"
    )
    output = common.execute_command(command_snapshot_file)

    assert output.get("exit_code", None) == 0
    assert "Environment provisioning complete" in output.get("output", "")

    cleanup()
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_force():
    """Verifies that the user can override the check to see if the resulting
    tarball exists."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "test", "--module", "test", "--force"],
        command_input="y\n",
    )

    run_assertions(result)
    assert "Creating snapshot of specified modules" in result.output

    cleanup()
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_no_scrub():
    """Verifies that the user config file is retained in full when scrubbing is
    disabled."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    utils.make_sample_config()
    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "test", "--module", "test", "--no-scrub"],
        True,
        command_input="y\n",
    )

    run_assertions(result)
    with open(snapshot_config_file()) as f:
        assert "*" * 20 not in f.read()

    cleanup()
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_scrub():
    """Verifies that sensitive data in user config file is scrubbed when
    scrubbing is enabled."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    utils.make_sample_config()
    result = utils.execute_cli_cmd(
        ["-v", "snapshot", "--name", "test", "--module", "test"], command_input="y\n"
    )

    run_assertions(result)
    with open(snapshot_config_file()) as f:
        assert "*" * 20 in f.read()

    cleanup()
    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def run_assertions(
    result, check_yaml=True, snapshot_name="test", check_path=common.SNAPSHOT_DIR
):
    """Runs standard assertions for the snapshot command."""

    if check_yaml:
        assert os.path.isfile(
            snapshot_test_yaml_file(snapshot_name)
        ), f"Not a valid file: {snapshot_test_yaml_file(snapshot_name)}"

    assert "Snapshot complete" in result.output
    assert result.exit_code == 0
    if os.path.isfile(os.path.join(common.MINITRINO_USER_DIR, "minitrino.cfg")):
        assert os.path.isfile(snapshot_config_file(snapshot_name))

    command_snapshot_file = os.path.join(
        common.MINITRINO_USER_SNAPSHOTS_DIR, snapshot_name, "provision-snapshot.sh"
    )
    assert os.path.isfile(command_snapshot_file)

    # Check that snapshot tarball exists
    assert os.path.isfile(os.path.join(check_path, f"{snapshot_name}.tar.gz"))

    with open(command_snapshot_file) as f:
        assert "minitrino -v --env LIB_PATH=" in f.read()


def cleanup(snapshot_name="test"):
    """Removes test snapshot tarball and turns off running resources."""

    if not snapshot_name == "test":
        common.execute_command(
            f"rm -rf {os.path.join(common.MINITRINO_USER_SNAPSHOTS_DIR, snapshot_name)}.tar.gz"
        )
    else:
        common.execute_command(f"rm -rf {common.SNAPSHOT_FILE}")

    utils.execute_cli_cmd(["down", "--sig-kill"])


if __name__ == "__main__":
    main()
