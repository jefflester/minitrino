"""Pytest configuration and fixtures for Minitrino CLI tests."""

import json
import logging
import sys
import time
from typing import Generator

import docker
import pytest

from minitrino.shutdown import shutdown_event
from tests import common
from tests.cli.constants import CLUSTER_NAME
from tests.cli.integration_tests import utils

executor = common.MinitrinoExecutor(CLUSTER_NAME)
logger = common.get_logger()


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
    # Use MINITRINO_TEST_LOG_LEVEL env var to set log level
    common.logger = common.get_logger()
    return common.logger


@pytest.fixture(autouse=True, scope="session")
def _setup_logger(_logger):
    pass


@pytest.fixture(autouse=True)
def _clear_shutdown_event() -> Generator:
    """
    Clear the global shutdown_event before each test.

    The shutdown_event is a global threading.Event that gets set when
    errors occur. Without clearing it between tests, it can contaminate
    subsequent tests with stale state, causing non-deterministic failures.
    """
    shutdown_event.clear()
    yield
    # Also clear after test to ensure clean state
    shutdown_event.clear()


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
    logger.info(f"START: {log_msg}")
    yield
    logger.info(f"END: {log_msg}")


@pytest.fixture
def down() -> Generator:
    """
    Bring down all running containers.

    Notes
    -----
    Runs after the test. Includes a brief delay to allow any
    background worker provisioning threads to complete before
    killing containers.
    """
    yield
    time.sleep(2)  # Allow background worker threads to complete
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
    logger.debug("Starting Docker daemon.")
    common.start_docker_daemon()
    yield


@pytest.fixture(scope="session")
def stop_docker() -> Generator:
    """
    Stop the Docker daemon.

    Notes
    -----
    Runs before the test. Docker is NOT restarted after the test
    session to avoid conflicts with pytest-rerunfailures. The next
    test run will start Docker via the start_docker fixture.
    """
    logger.debug("Stopping Docker daemon.")
    common.stop_docker_daemon()
    yield
    # Intentionally not restarting Docker - let next test run handle it
    logger.debug(
        "Docker daemon was stopped for daemon-off tests. "
        "Will be restarted in next test run."
    )


@pytest.fixture
def cleanup_config() -> Generator:
    """
    Ensure a sample config file and directory exist.

    Notes
    -----
    Runs before and after the test.
    """
    logger.debug("Running initial config cleanup (before test)")
    utils.cleanup_config()
    yield
    logger.debug("Running config cleanup (after test)")
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
        logger.debug(f"Resetting metadata for module: {module}")
        utils.write_file(path, json.dumps(default, indent=2))

    _helper()
    yield
    _helper()


@pytest.fixture
def build_test_image() -> Generator:
    """
    Build the test module image.

    Notes
    -----
    This fixture ensures the minitrino/test:latest image exists by
    provisioning and then bringing down the test cluster. Runs before
    the test.
    """
    logger.debug("Building test module image via provision")
    common.start_docker_daemon()
    logger.debug("Provisioning test module to build image")
    executor.exec(
        executor.build_cmd(
            "provision", cluster=CLUSTER_NAME, append=["--module", "test"]
        ),
        log_output=False,
    )
    logger.debug("Bringing down cluster but keeping image")
    executor.exec(
        executor.build_cmd("down", cluster=CLUSTER_NAME, append=["--sig-kill"]),
        log_output=False,
    )
    yield


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
    logger.debug("Starting Docker daemon for cluster provisioning.")
    common.start_docker_daemon()
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
        executor.exec(
            executor.build_cmd("provision", cluster=cluster, append=module_flags),
            log_output=False,
        )
    if not keepalive:
        down_cluster = "all" if len(cluster_names) > 1 else cluster_names[0]
        logger.debug(f"Bringing down cluster: {down_cluster}")
        executor.exec(
            executor.build_cmd("down", cluster=down_cluster, append=["--sig-kill"]),
            log_output=False,
        )
    yield


def pytest_runtest_logreport(report: pytest.TestReport):
    """
    Force pytest "PASS"/"FAIL" to log on its own line.

    Enhanced to detect and log test reruns from pytest-rerunfailures.
    """
    if report.when == "call":
        # Detect reruns from pytest-rerunfailures plugin
        if hasattr(report, "rerun") and report.rerun > 0:
            if report.failed:
                logger.warning(
                    f"⚠️  RETRYING TEST (attempt {report.rerun + 1}): "
                    f"{report.nodeid} - Note potential flakiness"
                )
            elif report.passed:
                logger.info(
                    f"✓ Test PASSED after retry: {report.nodeid} "
                    f"(succeeded on attempt {report.rerun + 1})"
                )

        if report.passed:
            sys.stdout.write("\n")
        elif report.failed:
            sys.stdout.write("\n")


def pytest_runtest_logstart():
    """Force pytest to log a newline after test start."""
    sys.stdout.write("\n")
