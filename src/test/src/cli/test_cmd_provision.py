#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import docker
import yaml

import src.common as common
import src.cli.utils as utils
from minitrino.settings import RESOURCE_LABEL
from minitrino.settings import MIN_SEP_VER

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
    test_bootstrap()
    test_enterprise()
    test_version_requirements()
    test_valid_user_config()
    test_duplicate_config_props()
    test_incompatible_modules()
    test_provision_append()
    test_workers()
    test_catalogs_volume()


def test_standalone():
    """Verifies that a standalone Trino container is provisioned when no
    options are passed in."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "provision"])

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

    result = utils.execute_cli_cmd(["-v", "--env", "STARBURST_VER=332-e", "provision"])

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

    result = utils.execute_cli_cmd(
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
    provisioning command."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(
        ["-v", "provision", "--module", "test", "--docker-native", "--build"]
    )

    containers = get_containers()
    assert "Received native Docker Compose options" in result.output
    assert len(containers) == 2

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_enterprise():
    """Ensures that the enterprise license checker works properly."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    utils.update_metadata_json("test", [{"enterprise": True}])
    result = utils.execute_cli_cmd(["-v", "provision", "--module", "test"])

    assert result.exit_code == 2
    assert "You must provide a path to a Starburst license" in result.output
    cleanup()

    # Create dummy license
    common.execute_command("touch /tmp/dummy.license")

    result = utils.execute_cli_cmd(
        [
            "-v",
            "--env",
            "LIC_PATH=/tmp/dummy.license",
            "provision",
            "--module",
            "test",
            "--no-rollback",
        ]
    )

    assert "LIC_PATH" and "/tmp/dummy.license" in result.output
    utils.reset_test_metadata_json()
    cleanup()

    # Ensure default dummy license satisfies Compose env vars
    result = utils.execute_cli_cmd(["-v", "provision", "--module", "test"])

    assert result.exit_code == 0
    etc_ls = common.execute_command(f"docker exec -i trino ls /etc/starburst/")
    assert "dummy.license" in etc_ls["output"]

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_version_requirements():
    """Ensures that module version requirements are properly enforced."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    utils.update_metadata_json("test", [{"versions": [MIN_SEP_VER + 1, 998]}])

    # Should fail - lower bound
    result = utils.execute_cli_cmd(
        [
            "-v",
            "--env",
            f"STARBURST_VER={MIN_SEP_VER}-e",
            "provision",
            "--module",
            "test",
        ]
    )

    assert result.exit_code == 2
    assert "minimum required" in result.output
    cleanup()

    # Should fail - upper bound
    result = utils.execute_cli_cmd(
        ["-v", "--env", "STARBURST_VER=999-e", "provision", "--module", "test"]
    )

    assert result.exit_code == 2
    assert "maximum required" in result.output

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    utils.reset_test_metadata_json()
    cleanup()


def test_bootstrap():
    """Ensures that bootstrap scripts properly execute in containers."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    def add_yaml_bootstrap(yaml_path=""):
        # In case left over from previous run
        del_yaml_bootstrap(yaml_path)

        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)

        for svc_name, svc_content in data.get("services", {}).items():
            if "environment" not in svc_content:
                svc_content["environment"] = {
                    "MINITRINO_BOOTSTRAP": f"bootstrap-{svc_name}.sh"
                }

        with open(yaml_path, "w") as file:
            yaml.dump(data, file, default_flow_style=False)

    def del_yaml_bootstrap(yaml_path=""):
        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)

        try:
            for _, svc_content in data.get("services", {}).items():
                if "environment" in svc_content:
                    del svc_content["environment"]
            with open(yaml_path, "w") as file:
                yaml.dump(data, file, default_flow_style=False)
        except:
            pass

    yaml_path = utils.get_module_yaml_path("test")
    add_yaml_bootstrap(yaml_path)

    result = utils.execute_cli_cmd(
        [
            "-v",
            "provision",
            "--module",
            "test",
        ]
    )

    assert all(
        (
            "Successfully executed bootstrap script in container 'trino'"
            in result.output,
            "Successfully executed bootstrap script in container 'test'"
            in result.output,
        )
    )

    trino_bootstrap = common.execute_command(
        f"docker exec -i trino cat /tmp/bootstrap.txt"
    )
    test_bootstrap = common.execute_command(
        f"docker exec -i test cat /tmp/bootstrap.txt"
    )

    assert "hello world" in trino_bootstrap.get("output", "") and test_bootstrap.get(
        "output", ""
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    del_yaml_bootstrap(yaml_path)
    cleanup()


def test_valid_user_config():
    """Ensures that valid, user-defined Trino/JVM config can be successfully
    appended to Trino config files."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(
        [
            "-v",
            "--env",
            "CONFIG_PROPERTIES=query.max-stage-count=85\nquery.max-execution-time=1h",
            "--env",
            "JVM_CONFIG=-Xms1G\n-Xmx2G",
            "provision",
            "--module",
            "test",
        ]
    )

    assert result.exit_code == 0
    assert (
        "Appending user-defined Trino config to Trino container config" in result.output
    )

    jvm_config = common.execute_command(
        f"docker exec -i trino cat /etc/starburst/jvm.config"
    )
    trino_config = common.execute_command(
        f"docker exec -i trino cat /etc/starburst/config.properties"
    )

    assert all(("-Xmx2G" in jvm_config["output"], "-Xms1G" in jvm_config["output"]))
    assert all(
        (
            "query.max-stage-count=85" in trino_config["output"],
            "query.max-execution-time=1h" in trino_config["output"],
        )
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_duplicate_config_props():
    """Ensures that duplicate configuration properties in Trino are logged as a
    warning to the user."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(
        [
            "-v",
            "--env",
            "CONFIG_PROPERTIES=query.max-stage-count=85\nquery.max-stage-count=100",
            "--env",
            "JVM_CONFIG=-Xms1G\n-Xms1G",
            "provision",
        ]
    )

    assert all(
        (
            "Duplicate Trino configuration properties detected in 'config.properties' file"
            in result.output,
            "query.max-stage-count=85" in result.output,
            "query.max-stage-count=100" in result.output,
            "Duplicate Trino configuration properties detected in 'jvm.config' file"
            in result.output,
            "-Xms1G" in result.output,
        )
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_incompatible_modules():
    """Verifies that chosen modules are not mutually-exclusive."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(
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

    utils.execute_cli_cmd(["-v", "provision", "--module", "test"])
    result = utils.execute_cli_cmd(["-v", "provision", "--module", "postgres"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "Identified the following running modules" in result.output
    assert len(containers) == 3  # trino, test, and postgres

    # Ensure new volume mount was activated; indicates Trino container was
    # properly recreated
    etc_ls = common.execute_command(f"docker exec -i trino ls /etc/starburst/catalog/")
    assert "postgres.properties" in etc_ls["output"]

    # Add one more module
    result = utils.execute_cli_cmd(["-v", "provision", "--module", "mysql"])
    etc_ls = common.execute_command(f"docker exec -i trino ls /etc/starburst/catalog/")
    assert "mysql.properties" and "postgres.properties" in etc_ls["output"]

    containers = get_containers()

    assert result.exit_code == 0
    assert len(containers) == 4  # trino, test, postgres, and mysql

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_workers():
    """Verifies that worker provisioning works."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    # Provision 1 worker
    result = utils.execute_cli_cmd(["-v", "provision", "--workers", "1"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "started worker container: 'trino-worker-1'" in result.output
    assert len(containers) == 2  # trino, trino worker

    # Provision a second worker
    result = utils.execute_cli_cmd(["-v", "provision", "--workers", "2"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "started worker container: 'trino-worker-2'" in result.output
    assert len(containers) == 3  # trino, (2) trino worker

    # Downsize workers (remove worker 2)
    result = utils.execute_cli_cmd(["-v", "provision", "--workers", "1"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "Removed excess worker" and "trino-worker-2" in result.output
    assert len(containers) == 2  # trino, trino worker

    # Provision a module in a running environment with a worker already present,
    # but don't specify any workers
    result = utils.execute_cli_cmd(["-v", "provision", "--module", "test"])
    containers = get_containers()

    assert result.exit_code == 0
    assert "Restarting container 'trino-worker-1'" in result.output
    assert len(containers) == 3  # trino, trino worker, test

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def test_catalogs_volume():
    """Verifies that the `catalogs` named volume functions as expected."""

    common.log_status(cast(FrameType, currentframe()).f_code.co_name)

    result = utils.execute_cli_cmd(["-v", "provision", "--module", "hive"])
    assert result.exit_code == 0

    hive = common.execute_command(
        "docker exec -i trino cat /etc/starburst/catalog/hive.properties"
    )

    assert "connector.name=hive" in hive["output"]

    cleanup()

    result = utils.execute_cli_cmd(
        ["-v", "provision", "--module", "hive", "--module", "delta-lake"]
    )
    assert result.exit_code == 0
    assert "Removed 'minitrino_catalogs' volume" in result.output

    hive = common.execute_command(
        "docker exec -i trino cat /etc/starburst/catalog/hive.properties"
    )
    delta = common.execute_command(
        "docker exec -i trino cat /etc/starburst/catalog/delta.properties"
    )

    assert (
        "connector.name=hive" in hive["output"]
        and "connector.name=delta-lake" in delta["output"]
    )

    common.log_success(cast(FrameType, currentframe()).f_code.co_name)
    cleanup()


def get_containers():
    """Returns all running minitrino containers."""

    docker_client = docker.from_env()
    return docker_client.containers.list(filters={"label": RESOURCE_LABEL})


def cleanup():
    """Brings down containers and removes resources."""

    utils.execute_cli_cmd(["down", "--sig-kill"])


if __name__ == "__main__":
    main()
