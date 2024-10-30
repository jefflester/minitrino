#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# TODO: Test no rollback
# TODO: Test invalid user config (Trino/JVM)

import docker
import time
import subprocess

import src.common as common
import src.cli.helpers as helpers
from minitrino.settings import RESOURCE_LABEL

from inspect import currentframe
from types import FrameType
from typing import cast


def main():
    common.log_status(__file__)
    common.start_docker_daemon()
    cleanup()
    test_standalone()
    test_bad_sep_version()
    test_invalid_module()
    test_docker_native()
    test_enterprise()
    test_valid_user_config()
    test_existing_user_config()
    test_duplicate_config_props()
    test_incompatible_modules()
    test_provision_append()
    test_workers()


def test_standalone():
    """Verifies that a standalone Trino container is provisioned when no
    options are passed in."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "provision"])

    assert result.exit_code == 0
    assert "Provisioning standalone" in result.output

    containers = get_containers()
    assert len(containers) == 1

    for container in containers:
        assert container.name == "trino"

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_bad_sep_version():
    """Verifies that a non-zero status code is returned when attempting to
    provide an invalid SEP version."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "--env", "STARBURST_VER=332-e", "provision"]
    )

    assert result.exit_code == 2
    assert "Provided Starburst version" in result.output

    containers = get_containers()
    assert len(containers) == 0

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_invalid_module():
    """Verifies that a non-zero status code is returned when attempting to
    provision an invalid module."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "provision", "--module", "hive", "--module", "not-a-real-module"]
    )

    assert result.exit_code == 2
    assert "Invalid module" in result.output

    containers = get_containers()
    assert len(containers) == 0

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_docker_native():
    """Ensures that native Docker Compose command options can be appended to the
    provisioning command.

    This function also calls the bootstrap script test functions."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        ["-v", "provision", "--module", "test", "--docker-native", "--build"]
    )

    containers = get_containers()
    assert "Received native Docker Compose options" in result.output
    assert len(containers) == 2

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)

    test_bootstrap_script(result)
    test_bootstrap_re_execute()
    cleanup()


def test_enterprise():
    """Ensures that the enterprise license checker works properly."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "provision", "--module", "test-enterprise"])

    assert result.exit_code == 2
    assert "You must provide a path to a Starburst license" in result.output
    cleanup()

    # Create dummy license
    process = subprocess.Popen(
        "touch /tmp/dummy.license",
        shell=True,
    )
    process.communicate()

    result = helpers.execute_command(
        [
            "-v",
            "--env",
            "LIC_PATH=/tmp/dummy.license",
            "provision",
            "--module",
            "test",
        ]
    )

    assert "LIC_PATH" and "/tmp/dummy.license" in result.output
    cleanup()

    result = helpers.execute_command(["-v", "provision", "--module", "test"])

    assert result.exit_code == 0
    assert "LIC_PATH" and "./modules/resources/dummy.license" in result.output
    assert "LIC_MOUNT_PATH" and "/etc/starburst/dummy.license:ro" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_bootstrap_script(result):
    """Ensures that bootstrap scripts properly execute in containers."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

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

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_bootstrap_re_execute():
    """Ensures that bootstrap scripts do not execute if they have already
    executed."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(["-v", "provision", "--module", "test"])

    assert result.exit_code == 0
    assert all(
        (
            "Bootstrap already executed in container 'trino'. Skipping.",
            "Bootstrap already executed in container 'test'. Skipping.",
        )
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)


def test_valid_user_config():
    """Ensures that valid, user-defined Trino/JVM config can be successfully
    appended to Trino config files."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = helpers.execute_command(
        [
            "-v",
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

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_existing_user_config():
    """Ensures that already-propagated configs are not propagated again, thus
    avoiding unnecessary container restarts."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.execute_command(
        [
            "-v",
            "provision",
            "--module",
            "test",
        ]
    )

    result = helpers.execute_command(
        [
            "-v",
            "provision",
            "--module",
            "test",
        ]
    )

    assert result.exit_code == 0
    assert "User-defined config already added to config files" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_duplicate_config_props():
    """Ensures that duplicate configuration properties in Trino are logged as a
    warning to the user."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.execute_command(["-v", "provision"])

    cmd_chunk = (
        f"'query.max-stage-count=85\nquery.max-stage-count=100"
        f"\nquery.max-execution-time=1h\nquery.max-execution-time=2h'"
    )
    subprocess.Popen(
        f'docker exec -i trino sh -c "echo {cmd_chunk} >> /etc/starburst/config.properties"',
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )

    cmd_chunk = "'-Xms1G\n-Xms1G'"
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
            "Duplicate Trino configuration properties detected in 'config.properties' file"
            in result.output,
            "query.max-stage-count=85" in result.output,
            "query.max-stage-count=100" in result.output,
            "query.max-execution-time=1h" in result.output,
            "query.max-execution-time=2h" in result.output,
            "Duplicate Trino configuration properties detected in 'jvm.config' file"
            in result.output,
            "-Xms1G" in result.output,
            "-Xms1G" in result.output,
        )
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_incompatible_modules():
    """Verifies that chosen modules are not mutually-exclusive."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

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

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_provision_append():
    """Verifies that modules can be appended to already-running environments."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    helpers.execute_command(["-v", "provision", "--module", "test"])
    result = helpers.execute_command(["-v", "provision", "--module", "postgres"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "Identified the following running modules" in result.output
    assert len(containers) == 3  # trino, test, and postgres

    # Ensure new volume mount was activated; indicates Trino container was
    # properly recreated
    etc_ls = subprocess.Popen(
        f"docker exec -i trino ls /etc/starburst/catalog/",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    etc_ls, _ = etc_ls.communicate()
    assert "postgres.properties" in etc_ls

    # Add one more module
    result = helpers.execute_command(["-v", "provision", "--module", "mysql"])
    etc_ls = subprocess.Popen(
        f"docker exec -i trino ls /etc/starburst/catalog/",
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    etc_ls, _ = etc_ls.communicate()
    assert "mysql.properties" and "postgres.properties" in etc_ls

    containers = get_containers()

    assert result.exit_code == 0
    assert len(containers) == 4  # trino, test, postgres, and mysql

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_workers():
    """Verifies that worker provisioning works."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    # Provision 1 worker
    result = helpers.execute_command(["-v", "provision", "--workers", "1"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "started worker container: 'trino-worker-1'" in result.output
    assert len(containers) == 2  # trino, trino worker

    # Provision a second worker
    result = helpers.execute_command(["-v", "provision", "--workers", "2"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "started worker container: 'trino-worker-2'" in result.output
    assert len(containers) == 3  # trino, (2) trino worker

    # Downsize workers (remove worker 2)
    result = helpers.execute_command(["-v", "provision", "--workers", "1"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "Removed excess worker" and "trino-worker-2" in result.output
    assert len(containers) == 2  # trino, trino worker

    # Provision a module in a running environment with a worker already present,
    # but don't specify any workers
    result = helpers.execute_command(["-v", "provision", "--module", "test"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "Restarting container 'trino-worker-1'" in result.output
    assert len(containers) == 3  # trino, trino worker, test

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
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
