#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import docker
import pathlib
import subprocess
import minipresto.test.helpers as helpers

from click.testing import CliRunner
from minipresto.cli import cli

snapshot_test_yaml_file = os.path.join(
    helpers.minipresto_user_snapshots_dir,
    "test",
    "lib",
    "modules",
    "catalog",
    "test",
    "test.yml",
)


def main():
    helpers.log_status("Running test_snapshot")
    test_daemon_off()
    test_snapshot_no_directory()
    test_snapshot_active_env()
    test_snapshot_inactive_env()
    test_force()
    test_scrub()
    test_no_scrub()


def test_daemon_off():
    """
    Verifies the command exits properly if the Docker daemon is off or
    unresponsive. Only applicable when trying to snapshot an active environment.
    """

    helpers.stop_docker_daemon()
    cleanup()

    runner = CliRunner()
    result = runner.invoke(cli, ["snapshot", "--name", "test"])
    assert result.exit_code == 1
    assert (
        "Error when pinging the Docker server. Is the Docker daemon running?"
        in result.output
    )

    helpers.log_status(f"Passed test_daemon_off")


def test_snapshot_no_directory():
    """
    Verifies that a snapshot can be created when there is no existing snapshots
    directory in the minipresto user home directory.
    """

    helpers.start_docker_daemon()
    cleanup()

    subprocess.call(f"rm -rf {helpers.minipresto_user_snapshots_dir}", shell=True)
    runner = CliRunner()
    result = runner.invoke(cli, ["snapshot", "--name", "test", "--catalog", "test"])

    run_assertions(result)
    assert os.path.isfile(snapshot_test_yaml_file)

    helpers.log_status(f"Passed test_snapshot_no_directory")


def test_snapshot_active_env():
    """
    Verifies that a snapshot can be successfully created from an active
    environment.
    """

    cleanup()

    runner = CliRunner()
    runner.invoke(cli, ["provision"])
    result = runner.invoke(cli, ["snapshot", "--name", "test"])

    run_assertions(result)
    assert "Creating snapshot of active environment" in result.output

    helpers.log_status(f"Passed test_snapshot_active_env")


def test_snapshot_inactive_env():
    """
    Verifies that a snapshot can be successfully created from an inactive
    environment.
    """

    cleanup()

    runner = CliRunner()
    result = runner.invoke(cli, ["snapshot", "--name", "test", "--catalog", "test"])

    run_assertions(result)
    assert "Creating snapshot of inactive environment" in result.output
    assert os.path.isfile(snapshot_test_yaml_file)

    helpers.log_status(f"Passed test_snapshot_inactive_env")


def test_force():
    """
    Verifies that the user can override the check to see if the resulting
    tarball exists.
    """

    runner = CliRunner()
    result = runner.invoke(
        cli, ["snapshot", "--name", "test", "--catalog", "test", "--force"]
    )

    run_assertions(result)
    assert "Creating snapshot of inactive environment" in result.output
    assert os.path.isfile(snapshot_test_yaml_file)

    cleanup()
    helpers.log_status(f"Passed test_force")


def test_no_scrub():
    """
    Verifies that the user config file is retained in full when scrubbing is
    disabled.
    """

    helpers.make_sample_config()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["snapshot", "--name", "test", "--catalog", "test", "--no-scrub"],
        input="y\n",
    )

    run_assertions(result)
    with open(helpers.snapshot_config_file) as f:
        assert "*" * 20 not in f.read()
    assert os.path.isfile(snapshot_test_yaml_file)

    cleanup()
    helpers.log_status(f"Passed test_no_scrub")


def test_scrub():
    """
    Verifies that sensitive data in user config file is scrubbed when scrubbing
    is enabled.
    """

    helpers.make_sample_config()

    runner = CliRunner()
    result = runner.invoke(cli, ["snapshot", "--name", "test", "--catalog", "test"])

    run_assertions(result)
    with open(helpers.snapshot_config_file) as f:
        assert "*" * 20 in f.read()
    assert os.path.isfile(snapshot_test_yaml_file)

    cleanup()
    helpers.log_status(f"Passed test_scrub")


def run_assertions(result):
    """Runs standard assertions for the snapshot command."""

    assert "Snapshot complete" in result.output
    assert result.exit_code == 0
    assert os.path.isfile(helpers.snapshot_config_file)

    command_snapshot_file = os.path.join(
        helpers.minipresto_user_snapshots_dir, "test", "provision-snapshot.sh"
    )
    assert os.path.isfile(command_snapshot_file)

    with open(command_snapshot_file) as f:
        assert "minipresto -v --lib-path" in f.read()


def cleanup():
    """
    Removes test snapshot tarball and turns off running resources.
    """

    subprocess.call(f"rm -rf {helpers.snapshot_file}", shell=True)
    runner = CliRunner()
    runner.invoke(cli, ["down"])


if __name__ == "__main__":
    main()
