"""Pytest configuration and fixtures for Minitrino CLI tests."""

import json
import logging
import os
import sys

import docker
import pytest

from test import common
from test.cli import utils
from test.cli.constants import CLUSTER_NAME
from test.cli.utils import logger
from test.common import CONFIG_FILE, MINITRINO_USER_DIR


@pytest.fixture
def docker_client() -> docker.DockerClient:
    """Return a Docker client for test use."""
    return utils.docker_client()[0]


@pytest.fixture(scope="session")
def _logger() -> logging.Logger:
    """Session-scoped logger for test output."""
    logger = logging.getLogger("minitrino.test")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(levelname)-8s %(name)s:%(filename)s:%(lineno)d %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


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
def log_test(log_msg: str) -> None:
    """
    Log a test start and end message.

    Parameters
    ----------
    log_msg : str
        The log message for the test.
    """
    logger.info(f"START: {log_msg}")
    yield
    logger.info(f"END: {log_msg}")


@pytest.fixture
def down() -> None:
    """
    Bring down all running containers.

    Notes
    -----
    Runs after the test.
    """
    yield
    utils.shut_down()


@pytest.fixture
def remove() -> None:
    """
    Remove resources for all modules in all clusters.

    Notes
    -----
    Runs after the test.
    """
    yield
    msg = "Removing all volumes and networks."
    utils.shut_down()
    logger.debug(msg)
    utils.cli_cmd(
        utils.build_cmd("remove", "all", append=["--volume", "--network"]),
        log_output=False,
    )


@pytest.fixture
def start_docker() -> None:
    """
    Start the Docker daemon.

    Notes
    -----
    Runs before the test.
    """
    logger.debug("Starting Docker daemon.")
    common.start_docker_daemon(logger)
    yield


@pytest.fixture(scope="module")
def stop_docker() -> None:
    """
    Stop the Docker daemon.

    Notes
    -----
    Runs before the test.
    """
    logger.debug("Stopping Docker daemon.")
    common.stop_docker_daemon()
    yield


@pytest.fixture
def cleanup_config() -> None:
    """
    Ensure a sample config file and directory exist.

    Notes
    -----
    Runs before and after the test.
    """

    def cleanup():
        logger.debug(f"Ensuring directory exists: {MINITRINO_USER_DIR}")
        os.makedirs(MINITRINO_USER_DIR, exist_ok=True)
        if os.path.isfile(CONFIG_FILE):
            logger.debug(f"Removing existing config file: {CONFIG_FILE}")
            os.remove(CONFIG_FILE)
        config = (
            "[config]\n"
            "LIB_PATH=\n"
            "CLUSTER_VER=\n"
            "TEXT_EDITOR=\n"
            "LIC_PATH=\n"
            "SECRET_KEY=abc123\n"
        )
        logger.debug(f"Writing sample config to: {CONFIG_FILE}")
        utils.write_file(CONFIG_FILE, config)

    logger.debug("Running initial config cleanup (before test)")
    cleanup()
    yield
    logger.debug("Running config cleanup (after test)")
    cleanup()


@pytest.fixture
def reset_metadata(request: pytest.FixtureRequest) -> None:
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
        logger.debug(f"Resetting metadata for module: {module}")
        utils.write_file(path, json.dumps(default, indent=2))

    _helper()
    yield
    _helper()


@pytest.fixture
def provision_clusters(request: pytest.FixtureRequest) -> None:
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
    logger.debug("Starting Docker daemon for cluster provisioning.")
    common.start_docker_daemon(logger)
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
        logger.debug(f"Provisioning cluster: {cluster}")
        utils.cli_cmd(
            utils.build_cmd("provision", cluster, append=module_flags), log_output=False
        )

    if not keepalive:
        down_cluster = "all" if len(cluster_names) > 1 else cluster_names[0]
        logger.debug(f"Bringing down cluster: {down_cluster}")
        utils.cli_cmd(
            utils.build_cmd("down", down_cluster, append=["--sig-kill"]),
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
