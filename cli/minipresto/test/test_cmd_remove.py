#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import docker
import subprocess
import minipresto.test.helpers as helpers

from minipresto.settings import RESOURCE_LABEL
from inspect import currentframe
from types import FrameType
from typing import cast

docker_client = docker.from_env()


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    cleanup()
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
    """Verifies that images with the standard Minipresto label applied to them
    are removed."""

    helpers.execute_command(["provision", "--module", "test"])
    helpers.execute_command(["down", "--sig-kill"])
    result = helpers.execute_command(["-v", "remove", "--images"])

    assert result.exit_code == 0
    assert "Image removed:" in result.output

    assert_docker_resource_count(
        {
            "resource_type": docker_client.images,
            "label": RESOURCE_LABEL,
            "expected_count": 0,
        }
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_volumes():
    """Verifies that volumes with the standard Minipresto label applied to them
    are removed."""

    helpers.execute_command(["provision", "--module", "test"])
    helpers.execute_command(["down", "--sig-kill"])
    result = helpers.execute_command(["-v", "remove", "--volumes"])

    assert result.exit_code == 0
    assert "Volume removed:" in result.output

    assert_docker_resource_count(
        {
            "resource_type": docker_client.volumes,
            "label": RESOURCE_LABEL,
            "expected_count": 0,
        }
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_label():
    """Verifies that only images with the given label are removed."""

    helpers.execute_command(["provision", "--module", "test"])
    helpers.execute_command(["down", "--sig-kill"])
    result = helpers.execute_command(
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

    assert_docker_resource_count(
        {
            "resource_type": docker_client.images,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 0,
        },
        {
            "resource_type": docker_client.images,
            "label": "com.starburst.tests.module=presto",
            "expected_count": 1,
        },
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_multiple_labels():
    """Verifies that images with any of the given labels are removed."""

    helpers.execute_command(["provision", "--module", "test"])
    helpers.execute_command(["down", "--sig-kill"])
    result = helpers.execute_command(
        [
            "-v",
            "remove",
            "--volumes",
            "--label",
            "com.starburst.tests.module.test=catalog-test",
            "--label",
            RESOURCE_LABEL,
        ],
    )

    assert result.exit_code == 0
    assert "Volume removed:" in result.output

    assert_docker_resource_count(
        {
            "resource_type": docker_client.volumes,
            "label": RESOURCE_LABEL,
            "expected_count": 0,
        },
        {
            "resource_type": docker_client.volumes,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 0,
        },
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_invalid_label():
    """Verifies that images with the Minipresto label applied to them are
    removed."""

    helpers.execute_command(["provision", "--module", "test"])
    helpers.execute_command(["down", "--sig-kill"])
    result = helpers.execute_command(
        ["-v", "remove", "--images", "--label", "not-real-label=not-real"]
    )

    assert result.exit_code == 0
    assert "Image removed:" not in result.output

    assert_docker_resource_count(
        {
            "resource_type": docker_client.images,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 1,
        }
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_all():
    """Verifies that all Minipresto resources are removed."""

    helpers.execute_command(["provision", "--module", "test"])
    helpers.execute_command(["down", "--sig-kill"])
    result = helpers.execute_command(["-v", "remove", "--images", "--volumes"])

    assert result.exit_code == 0
    assert all(("Volume removed:" in result.output, "Image removed:" in result.output))

    assert_docker_resource_count(
        {
            "resource_type": docker_client.images,
            "label": RESOURCE_LABEL,
            "expected_count": 0,
        },
        {
            "resource_type": docker_client.volumes,
            "label": RESOURCE_LABEL,
            "expected_count": 0,
        },
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_remove_dependent_resources_running():
    """Verifies that a dependent resources (tied to active containers) cannot be
    removed."""

    helpers.execute_command(["provision", "--module", "test"])
    result = helpers.execute_command(["-v", "remove", "--images", "--volumes"])

    assert result.exit_code == 0
    assert all(
        (
            "Cannot remove volume:" in result.output,
            "Cannot remove image:" in result.output,
        )
    )

    assert_docker_resource_count(
        {
            "resource_type": docker_client.images,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 1,
        },
        {
            "resource_type": docker_client.volumes,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 1,
        },
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_remove_dependent_resources_stopped():
    """Verifies that a dependent resources (tied to stopped containers) cannot
    be removed."""

    helpers.execute_command(["provision", "--module", "test"])
    subprocess.call("docker stop test", shell=True)
    result = helpers.execute_command(
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
    assert all(
        (
            "Cannot remove volume:" in result.output,
            "Cannot remove image:" in result.output,
        )
    )

    assert_docker_resource_count(
        {
            "resource_type": docker_client.images,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 1,
        },
        {
            "resource_type": docker_client.volumes,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 1,
        },
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_remove_dependent_resources_force():
    """Verifies that a dependent resources can be forcibly removed. Note that
    even forcing a resource removal will not work if it is tied to a running
    container.

    Images can be forcibly removed if tied to a stop container. Volumes cannot
    be removed if tied to any container, whether it is active or stopped. This
    is a Docker-level restriction."""

    helpers.execute_command(["provision", "--module", "test"])
    subprocess.call("docker stop test", shell=True)
    result = helpers.execute_command(
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

    assert_docker_resource_count(
        {
            "resource_type": docker_client.images,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 0,
        },
        {
            "resource_type": docker_client.volumes,
            "label": "com.starburst.tests.module.test=catalog-test",
            "expected_count": 1,
        },
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def assert_docker_resource_count(*args):
    """Asserts the accuracy of the count returned from a Docker resource lookup.
    Accepts variable number of dictionaries and will perform processing for each
    dictionary.

    - `resource_type`: Resource type (container, volume, image)
    - `label`: Label to filter by
    - `expected_count`: The expected length of the returned list"""

    for arg in args:
        resource_type = arg.get("resource_type", None)
        label = arg.get("label", None)
        expected_count = arg.get("expected_count", None)
        resource_list = resource_type.list(filters={"label": label})
        assert len(resource_list) == expected_count


def cleanup():
    """Brings down containers and removes resources."""

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
