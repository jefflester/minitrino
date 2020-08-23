#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import docker
import subprocess
import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    test_images()
    test_volumes()
    test_label()
    test_multiple_labels()
    test_invalid_label()
    test_all()
    test_remove_dependent_resources_running()
    test_remove_dependent_resources_stopped()
    test_remove_dependent_resources_force()


def test_images():
    """
    Verifies that images with the minipresto label applied to them are removed.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    helpers.execute_command(["down"])
    result = helpers.initialize_test(["-v", "remove", "--images"])

    assert result.exit_code == 0
    assert "Image removed:" in result.output

    docker_client = docker.from_env()
    images = docker_client.images.list(
        filters={"label": "com.starburst.tests.module.test=catalog-test"}
    )
    assert len(images) == 0

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_volumes():
    """
    Verifies that volumes with the minipresto label applied to them are removed.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    helpers.execute_command(["down"])
    result = helpers.initialize_test(["-v", "remove", "--volumes"])

    assert result.exit_code == 0
    assert "Volume removed:" in result.output

    docker_client = docker.from_env()
    volumes = docker_client.volumes.list(
        filters={"label": "com.starburst.tests.module.test=catalog-test"}
    )
    assert len(volumes) == 0

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_label():
    """
    Verifies that images with the minipresto label applied to them are removed.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    helpers.execute_command(["down"])
    result = helpers.initialize_test(
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

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_multiple_labels():
    """
    Verifies that images with the minipresto label applied to them are removed.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    helpers.execute_command(["down"])
    result = helpers.initialize_test(
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

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_invalid_label():
    """
    Verifies that images with the minipresto label applied to them are removed.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    helpers.execute_command(["down"])
    result = helpers.initialize_test(
        ["-v", "remove", "--images", "--label", "not-real-label=not-real"]
    )

    assert result.exit_code == 0
    assert "Image removed:" not in result.output

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_all():
    """
    Verifies that all minipresto resources are removed.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    helpers.execute_command(["down"])
    result = helpers.initialize_test(["-v", "remove", "--images", "--volumes"])

    assert result.exit_code == 0
    assert all(("Volume removed:" in result.output, "Image removed:" in result.output))

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_remove_dependent_resources_running():
    """
    Verifies that a dependent resources (tied to active containers)
    cannot be removed.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    result = helpers.initialize_test(["-v", "remove", "--images", "--volumes"])

    assert result.exit_code == 0
    assert all(
        (
            "Cannot remove volume:" in result.output,
            "Cannot remove image:" in result.output,
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_remove_dependent_resources_stopped():
    """
    Verifies that a dependent resources (tied to stopped containers)
    cannot be removed.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    subprocess.call("docker stop test", shell=True)
    result = helpers.initialize_test(
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

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_remove_dependent_resources_force():
    """
    Verifies that a dependent resources can be forcibly removed. Note that even
    forcing a resource removal will not work if it is tied to a running
    container.

    Images can be forcibly removed if tied to a stop container. Volumes cannot
    be removed if tied to any container, whether it is active or stopped. This
    is a Docker-level restriction.
    """

    helpers.execute_command(["provision", "--catalog", "test"])
    subprocess.call("docker stop test", shell=True)
    result = helpers.initialize_test(
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

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def cleanup():
    """
    Brings down containers and removes resources.
    """

    helpers.execute_command(
        [
            "remove",
            "--images",
            "--volumes",
            "--label",
            "com.starburst.tests.module.test=catalog-test",
        ]
    )


if __name__ == "__main__":
    main()
