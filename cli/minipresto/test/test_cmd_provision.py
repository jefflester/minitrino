#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# TODO: Test no rollback
# TODO: Test invalid user config (Presto/JVM)

import os
import docker
import subprocess
import minipresto.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast
from minipresto.settings import RESOURCE_LABEL


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    test_standalone()
    test_invalid_module()
    test_docker_native()
    test_valid_user_config()


def test_standalone():
    """Verifies that a standalone Presto container is provisioned when no
    options are passed in."""

    result = helpers.execute_command(["-v", "provision"])

    assert result.exit_code == 0
    assert "Provisioning standalone" in result.output

    containers = get_containers()
    assert len(containers) == 1

    for container in containers:
        assert container.name == "presto"

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_invalid_module():
    """Verifies that a non-zero status code is returned when attempting to
    provision an invalid module."""

    result = helpers.execute_command(
        ["-v", "provision", "--module", "hive-s3", "--module", "not-a-real-module"]
    )

    assert result.exit_code == 2
    assert "Invalid module" in result.output

    containers = get_containers()
    assert len(containers) == 0

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_docker_native():
    """Ensures that native Docker Compose command options can be appended to the
    provisioning command.

    This function also calls the bootstrap script test functions."""

    result = helpers.execute_command(
        ["-v", "provision", "--module", "test", "--docker-native", "build"]
    )

    containers = get_containers()
    assert "Received native Docker Compose options" in result.output
    assert len(containers) == 2

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)

    test_bootstrap_script(result)
    test_bootstrap_re_execute()
    cleanup()


def test_bootstrap_script(result):
    """Ensures that bootstrap scripts properly execute in containers."""

    assert all(
        (
            "Successfully executed bootstrap script in container: 'presto'",
            "Successfully executed bootstrap script in container: 'test'",
        )
    )

    presto_bootstrap_check = subprocess.Popen(
        f"docker exec -i presto ls /usr/lib/presto/etc/",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    test_bootstrap_check = subprocess.Popen(
        f"docker exec -i test cat /root/test_bootstrap.txt",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    presto_bootstrap_check, _ = presto_bootstrap_check.communicate()
    test_bootstrap_check, _ = test_bootstrap_check.communicate()

    assert "test_bootstrap.txt" in presto_bootstrap_check
    assert "hello world" in test_bootstrap_check

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_bootstrap_re_execute():
    """Ensures that bootstrap scripts do not execute if they have already
    executed."""

    result = helpers.execute_command(
        ["-v", "provision", "--module", "test", "--docker-native", "build"]
    )

    assert result.exit_code == 0
    assert all(
        (
            "Bootstrap already executed in container 'presto'. Skipping.",
            "Bootstrap already executed in container 'test'. Skipping.",
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_valid_user_config():
    """Ensures that valid, user-defined Presto/JVM config can be successfully
    appended to Presto config files.

    This function also calls the function that checks for the effectiveness of
    the duplicate config checker."""

    user_config = """
    [PRESTO]
    CONFIG=
        query.max-stage-count=85
        query.max-execution-time=1h
    JVM_CONFIG=
        -Xmx=2G
        -Xms=1G
        -Xms=1G
    """

    subprocess.call(
        f'bash -c "cat << EOF > {helpers.CONFIG_FILE}\n' f"{user_config}",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    result = helpers.execute_command(["-v", "provision", "--module", "test"])

    assert result.exit_code == 0
    assert (
        "Appending Presto config from minipresto.cfg to Presto config files"
        in result.output
    )

    jvm_config = subprocess.Popen(
        f"docker exec -i test cat /usr/lib/presto/etc/jvm.config",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    presto_config = subprocess.Popen(
        f"docker exec -i test cat /usr/lib/presto/etc/config.properties",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    jvm_config, _ = jvm_config.communicate()
    presto_config, _ = presto_config.communicate()

    assert all(("-Xmx=2G", "-Xms=1G")) in jvm_config
    assert (
        all(("query.max-stage-count=85", "query.max-execution-time=1h"))
        in presto_config
    )

    test_duplicate_config_props(result)

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_duplicate_config_props(result):
    """Ensures that duplicate configuration properties in Presto are logged as a
    warning to the user."""

    assert all(
        (
            "Duplicate Presto configuration properties detected in config.properties",
            "query.max-stage-count=85",
            "query.max-execution-time=1h",
            "Duplicate Presto configuration properties detected in jvm.config",
            "-Xms=1G" in result.output,
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def get_containers():
    """Returns all running minipresto containers."""

    docker_client = docker.from_env()
    return docker_client.containers.list(filters={"label": RESOURCE_LABEL})


def cleanup():
    """Brings down containers and removes resources."""

    helpers.execute_command(["down", "--sig-kill"])


if __name__ == "__main__":
    main()
