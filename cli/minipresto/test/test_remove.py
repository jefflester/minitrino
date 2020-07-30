#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import docker
import subprocess
import minipresto.test.helpers as helpers

from click.testing import CliRunner
from minipresto.cli import cli


def main():
    helpers.log_status("Running test_remove")
    test_daemon_off()
    test_images()
    test_volumes()
    test_label()
    test_multiple_labels()
    test_invalid_label()
    test_all()
    test_remove_dependent_resources_running()
    test_remove_dependent_resources_stopped()
    test_remove_dependent_resources_force()


def test_daemon_off():
    """
    Verifies the command exits properly if the Docker daemon is off or
    unresponsive.
    """

    helpers.stop_docker_daemon()

    runner = CliRunner()
    result = runner.invoke(cli, ["remove"])
    assert result.exit_code == 1
    assert (
        "Error when pinging the Docker server. Is the Docker daemon running?"
        in result.output
    )

    helpers.log_status(f"Passed test_daemon_off")


def test_images():
    """
    Verifies that images with the minipresto label applied to them are removed.
    """

    helpers.start_docker_daemon()

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    runner.invoke(cli, ["down"])
    result = runner.invoke(cli, ["-v", "remove", "--images"])
    assert result.exit_code == 0
    assert "Image removed:" in result.output

    docker_client = docker.from_env()
    images = docker_client.images.list(
        filters={"label": "com.starburst.tests.module.test=catalog-test"}
    )

    assert len(images) == 0

    helpers.log_status(f"Passed test_images")
    cleanup(runner)


def test_volumes():
    """
    Verifies that volumes with the minipresto label applied to them are removed.
    """

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    runner.invoke(cli, ["down"])
    result = runner.invoke(cli, ["-v", "remove", "--volumes"])
    assert result.exit_code == 0
    assert "Volume removed:" in result.output

    docker_client = docker.from_env()
    volumes = docker_client.volumes.list(
        filters={"label": "com.starburst.tests.module.test=catalog-test"}
    )

    assert len(volumes) == 0

    helpers.log_status(f"Passed test_volumes")
    cleanup(runner)


def test_label():
    """
    Verifies that images with the minipresto label applied to them are removed.
    """

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    runner.invoke(cli, ["down"])
    result = runner.invoke(
        cli,
        [
            "-v",
            "remove",
            "--images",
            "--label",
            "com.starburst.tests.module.test=catalog-test",
        ],
    )
    assert result.exit_code == 0
    assert "Image removed:" in result.output

    docker_client = docker.from_env()
    images = docker_client.images.list(
        filters={"label": "com.starburst.tests.module.test=catalog-test"}
    )

    assert len(images) == 0

    helpers.log_status(f"Passed test_label")
    cleanup(runner)


def test_multiple_labels():
    """
    Verifies that images with the minipresto label applied to them are removed.
    """

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    runner.invoke(cli, ["down"])
    result = runner.invoke(
        cli,
        [
            "-v",
            "remove",
            "--volumes",
            "--label",
            "com.starburst.tests.module.test=catalog-test",
            "com.starburst.tests=minipresto",
        ],
    )
    assert result.exit_code == 0
    assert "Volume removed:" in result.output

    docker_client = docker.from_env()
    volumes = docker_client.volumes.list(
        filters={"label": "com.starburst.tests.module.test=catalog-test"}
    )

    assert len(volumes) == 0

    helpers.log_status(f"Passed test_multiple_labels")
    cleanup(runner)


def test_invalid_label():
    """
    Verifies that images with the minipresto label applied to them are removed.
    """

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    runner.invoke(cli, ["down"])
    result = runner.invoke(
        cli, ["-v", "remove", "--images", "--label", "not-real-label=not-real"]
    )
    assert result.exit_code == 0
    assert "Image removed:" not in result.output
    helpers.log_status(f"Passed test_invalid_label")
    cleanup(runner)


def test_all():
    """
    Verifies that all minipresto resources are removed.
    """

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    runner.invoke(cli, ["down"])
    result = runner.invoke(cli, ["-v", "remove", "--images", "--volumes"])
    assert result.exit_code == 0
    assert all(("Volume removed:" in result.output, "Image removed:" in result.output))
    helpers.log_status(f"Passed test_all")
    cleanup(runner)


def test_remove_dependent_resources_running():
    """
    Verifies that a dependent resources (tied to active containers)
    cannot be removed.
    """

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    result = runner.invoke(cli, ["-v", "remove", "--images", "--volumes"])
    assert result.exit_code == 0
    assert all(
        (
            "Cannot remove volume:" in result.output,
            "Cannot remove image:" in result.output,
        )
    )
    helpers.log_status(f"Passed test_remove_dependent_resources_running")
    cleanup(runner)


def test_remove_dependent_resources_stopped():
    """
    Verifies that a dependent resources (tied to stopped containers)
    cannot be removed.
    """

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    subprocess.call("docker stop test", shell=True)
    result = runner.invoke(
        cli,
        [
            "-v",
            "remove",
            "--images",
            "--volumes",
            "--label",
            "com.starburst.tests.module.test=catalog-test",
        ],
    )
    assert result.exit_code == 0
    assert "Cannot remove volume:" in result.output
    helpers.log_status(f"Passed test_remove_dependent_resources_stopped")
    cleanup(runner)


def test_remove_dependent_resources_force():
    """
    Verifies that a dependent resources can be forcibly removed. Note that even
    forcing a resource removal will not work if it is tied to a running
    container.

    Images can be forcibly removed if tied to a stop container. Volumes cannot
    be removed if tied to any container, whether it is active or stopped. This
    is a Docker-level restriction.
    """

    runner = CliRunner()
    runner.invoke(cli, ["provision", "--catalog", "test"])
    subprocess.call("docker stop test", shell=True)
    result = runner.invoke(
        cli,
        [
            "-v",
            "remove",
            "--images",
            "--label",
            "com.starburst.tests.module.test=catalog-test",
            "--force",
        ],
    )
    assert result.exit_code == 0
    assert "Image removed:" in result.output
    helpers.log_status(f"Passed test_remove_dependent_resources_force")
    cleanup(runner)


def cleanup(runner):
    """
    Brings down containers and removes resources.
    """

    runner.invoke(cli, ["down"])
    runner.invoke(
        cli,
        [
            "remove",
            "--images",
            "--volumes",
            "--label",
            "com.starburst.tests.module.test=catalog-test",
        ],
    )


if __name__ == "__main__":
    main()
