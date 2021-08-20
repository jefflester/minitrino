#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# TODO: Test no rollback
# TODO: Test invalid user config (Trino/JVM)

import os
import docker
import time
import subprocess
import minitrino.test.helpers as helpers

from inspect import currentframe
from types import FrameType
from typing import cast
from minitrino.settings import RESOURCE_LABEL


def main():
    helpers.log_status(__file__)
    helpers.start_docker_daemon()
    cleanup()
    test_standalone()
    test_bad_sep_version()
    test_invalid_module()
    test_docker_native()
    test_valid_user_config()
    test_duplicate_config_props()
    test_incompatible_modules()
    test_provision_append()


def test_standalone():
    """Verifies that a standalone Trino container is provisioned when no
    options are passed in."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "provision"])

    assert result.exit_code == 0
    assert "Provisioning standalone" in result.output

    containers = get_containers()
    assert len(containers) == 1

    for container in containers:
        assert container.name == "trino"

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_bad_sep_version():
    """Verifies that a non-zero status code is returned when attempting to
    provide an invalid SEP version."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "--env", "STARBURST_VER=332-e", "provision"]
    )

    assert result.exit_code == 2
    assert "Invalid Starburst version" in result.output

    containers = get_containers()
    assert len(containers) == 0

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_invalid_module():
    """Verifies that a non-zero status code is returned when attempting to
    provision an invalid module."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

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

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "provision", "--module", "test", "--docker-native", "--build"]
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

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    assert all(
        (
            "Successfully executed bootstrap script in container: 'trino'",
            "Successfully executed bootstrap script in container: 'test'",
        )
    )

    trino_bootstrap_check = subprocess.Popen(
        f"docker exec -i trino ls /etc/starburst/",
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

    trino_bootstrap_check, _ = trino_bootstrap_check.communicate()
    test_bootstrap_check, _ = test_bootstrap_check.communicate()

    assert "test_bootstrap.txt" in trino_bootstrap_check
    assert "hello world" in test_bootstrap_check

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_bootstrap_re_execute():
    """Ensures that bootstrap scripts do not execute if they have already
    executed."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "provision", "--module", "test"])

    assert result.exit_code == 0
    assert all(
        (
            "Bootstrap already executed in container 'trino'. Skipping.",
            "Bootstrap already executed in container 'test'. Skipping.",
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_valid_user_config():
    """Ensures that valid, user-defined Trino/JVM config can be successfully
    appended to Trino config files."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        [
            "-v",
            "--env",
            "CONFIG=query.max-stage-count=85\nquery.max-execution-time=1h",
            "--env",
            "JVM_CONFIG=-Xmx2G\n-Xms1G",
            "provision",
            "--module",
            "test",
        ]
    )

    assert result.exit_code == 0
    assert (
        "Appending user-defined Trino config to Trino container config" in result.output
    )

    jvm_config = subprocess.Popen(
        f"docker exec -i trino cat /etc/starburst/jvm.config",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    trino_config = subprocess.Popen(
        f"docker exec -i trino cat /etc/starburst/config.properties",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    jvm_config, _ = jvm_config.communicate()
    trino_config, _ = trino_config.communicate()

    assert all(("-Xmx2G" in jvm_config, "-Xms1G" in jvm_config))
    assert all(
        (
            "query.max-stage-count=85" in trino_config,
            "query.max-execution-time=1h" in trino_config,
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_duplicate_config_props():
    """Ensures that duplicate configuration properties in Trino are logged as a
    warning to the user."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.execute_command(["-v", "provision"])

    cmd_chunk = (
        f"$'query.max-stage-count=85\nquery.max-stage-count=100"
        f"\nquery.max-execution-time=1h\nquery.max-execution-time=2h'"
    )
    subprocess.Popen(
        f'docker exec -i trino sh -c "echo {cmd_chunk} >> /etc/starburst/config.properties"',
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    cmd_chunk = "$'-Xms1G\n-Xms1G'"
    subprocess.Popen(
        f'docker exec -i trino sh -c "echo {cmd_chunk} >> /etc/starburst/jvm.config"',
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    # Hard stop to allow commands to process
    time.sleep(2)

    helpers.execute_command(["-v", "down", "--sig-kill", "--keep"])
    result = helpers.execute_command(["-v", "provision"])

    assert all(
        (
            "Duplicate Trino configuration properties detected in config.properties"
            in result.output,
            "query.max-stage-count=85" in result.output,
            "query.max-stage-count=100" in result.output,
            "query.max-execution-time=1h" in result.output,
            "query.max-execution-time=2h" in result.output,
            "Duplicate Trino configuration properties detected in jvm.config"
            in result.output,
            "-Xms1G" in result.output,
            "-Xms1G" in result.output,
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_incompatible_modules():
    """Verifies that chosen modules are not mutually-exclusive."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "provision", "--module", "ldap", "--module", "test"]
    )

    assert result.exit_code == 2
    assert all(
        (
            "Incompatible modules detected" in result.output,
            "incompatible with module" in result.output,
            "ldap" in result.output,
        )
    )

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_provision_append():
    """Verifies that modules can be appended to already-running environments."""

    helpers.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.execute_command(["-v", "provision", "--module", "test"])
    result = helpers.execute_command(["-v", "provision", "--module", "postgres"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "Identified the following running modules" in result.output
    assert len(containers) == 3  # trino, test, and postgres

    helpers.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def get_containers():
    """Returns all running minitrino containers."""

    docker_client = docker.from_env()
    return docker_client.containers.list(filters={"label": RESOURCE_LABEL})


def cleanup():
    """Brings down containers and removes resources."""

    helpers.execute_command(["down", "--sig-kill"])


if __name__ == "__main__":
    main()
