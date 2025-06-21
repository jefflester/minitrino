"""Pytest configuration and fixtures for Minitrino CLI tests."""

import json
import logging
import sys
from typing import Generator

import docker
import pytest

from tests import common
from tests.cli import utils
from tests.cli.constants import CLUSTER_NAME

builder = common.CLICommandBuilder(CLUSTER_NAME)


def pytest_sessionstart(session):
    """Run pre-work before any tests are collected or run."""
    utils.remove()
    utils.cleanup_config()


@pytest.fixture
def docker_client() -> docker.DockerClient:
    """Return a Docker client for test use."""
    return utils.docker_client()[0]


@pytest.fixture(scope="session")
def _logger() -> logging.Logger:
    """Session-scoped logger for test output."""
    return common.get_logger()


@pytest.fixture(autouse=True, scope="session")
def _setup_logger(_logger):
    pass


@pytest.fixture
def log_msg(request: pytest.FixtureRequest) -> str:
    """
    Return the log message for a test.

    Parameters
    ----------
    request : pytest.FixtureRequest
        The pytest fixture request.

    Returns
    -------
    str
        The log message for the test.
    """
    return str(getattr(request, "param", ""))


@pytest.fixture
def log_test(log_msg: str) -> Generator:
    """
    Log a test start and end message.

    Parameters
    ----------
    log_msg : str
        The log message for the test.
    """
    common.logger.info(f"START: {log_msg}")
    yield
    common.logger.info(f"END: {log_msg}")


@pytest.fixture
def down() -> Generator:
    """
    Bring down all running containers.

    Notes
    -----
    Runs after the test.
    """
    yield
    utils.shut_down()


@pytest.fixture
def remove() -> Generator:
    """
    Remove resources for all modules in all clusters.

    Notes
    -----
    Runs after the test.
    """
    yield
    utils.remove()


@pytest.fixture
def start_docker() -> Generator:
    """
    Start the Docker daemon.

    Notes
    -----
    Runs before the test.
    """
    common.logger.debug("Starting Docker daemon.")
    common.start_docker_daemon(common.logger)
    yield


@pytest.fixture(scope="session")
def stop_docker() -> Generator:
    """
    Stop the Docker daemon.

    Notes
    -----
    Runs before the test.
    """
    common.logger.debug("Stopping Docker daemon.")
    common.stop_docker_daemon()
    yield
    common.start_docker_daemon(common.logger)


@pytest.fixture
def cleanup_config() -> Generator:
    """
    Ensure a sample config file and directory exist.

    Notes
    -----
    Runs before and after the test.
    """
    common.logger.debug("Running initial config cleanup (before test)")
    utils.cleanup_config()
    yield
    common.logger.debug("Running config cleanup (after test)")
    utils.cleanup_config()


@pytest.fixture
def reset_metadata(request: pytest.FixtureRequest) -> Generator:
    """
    Reset the given module's `metadata.json` file to default values.

    Parameters
    ----------
    request : pytest.FixtureRequest
        The pytest fixture request.

    Notes
    -----
    Module defaults to `test` if not specified. Runs before and after
    the test.
    """

    def _helper():
        module = getattr(request, "param", "test")
        default = {
            "description": "Test module.",
            "incompatibleModules": ["ldap"],
            "dependentModules": ["file-access-control"],
            "versions": [],
            "enterprise": False,
            "dependentClusters": [],
        }
        path = utils.get_metadata_json_path(module)
        common.logger.debug(f"Resetting metadata for module: {module}")
        utils.write_file(path, json.dumps(default, indent=2))

    _helper()
    yield
    _helper()


@pytest.fixture
def provision_clusters(request: pytest.FixtureRequest) -> Generator:
    """
    Provision one or more clusters with the `test` module by default.

    Parameters
    ----------
    request : pytest.FixtureRequest
        The pytest fixture request.

    Notes
    -----
    Shuts down the clusters after creation unless `keepalive` is set to
    `True`.
    """
    common.logger.debug("Starting Docker daemon for cluster provisioning.")
    common.start_docker_daemon(common.logger)
    param = getattr(request, "param", {})
    cluster_names = param.get("cluster_names", [CLUSTER_NAME])
    modules = param.get("modules", ["test"])
    no_modules = param.get("no_modules", False)
    keepalive = param.get("keepalive", False)

    if CLUSTER_NAME not in cluster_names:
        cluster_names.append(CLUSTER_NAME)
    if "test" not in modules:
        modules.append("test")

    module_flags = []
    if not no_modules:
        for module in modules:
            module_flags.extend(["--module", module])

    for cluster in cluster_names:
        common.logger.debug(f"Provisioning cluster: {cluster}")
        common.cli_cmd(
            builder.build_cmd("provision", append=module_flags),
            log_output=False,
        )
    if not keepalive:
        down_cluster = "all" if len(cluster_names) > 1 else cluster_names[0]
        common.logger.debug(f"Bringing down cluster: {down_cluster}")
        common.cli_cmd(
            builder.build_cmd("down", append=["--sig-kill"]),
            log_output=False,
        )
    yield


def pytest_runtest_logreport(report: pytest.TestReport):
    """Force pytest "PASS"/"FAIL" to log on its own line."""
    if report.when == "call":
        if report.passed:
            sys.stdout.write("\n")
        elif report.failed:
            sys.stdout.write("\n")


def pytest_runtest_logstart():
    """Force pytest to log a newline after test start."""
    sys.stdout.write("\n")
