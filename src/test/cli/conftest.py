"""Pytest configuration and fixtures for Minitrino CLI tests."""

import os
import io
import sys
import json
import docker
import pytest
import logging

from test import common
from test.cli import utils
from test.cli.constants import CLUSTER_NAME

from test.common import (
    MINITRINO_USER_DIR,
    CONFIG_FILE,
    SNAPSHOT_FILE,
    MINITRINO_USER_SNAPSHOTS_DIR,
)


@pytest.fixture
def docker_client() -> docker.DockerClient:
    """Return a Docker client for test use."""
    return docker.from_env()


@pytest.fixture(scope="session")
def logger() -> logging.Logger:
    """Session-scoped logger for test output."""
    logger = logging.getLogger("minitrino.test")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if reloaded
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


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
    return str(request.param)


@pytest.fixture
def log_test(log_msg: str, logger: logging.Logger) -> None:
    """
    Log a test start and end message.

    Parameters
    ----------
    log_msg : str
        The log message for the test.
    logger : logging.Logger
        The logger instance.
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
    utils.shut_down()
    utils.cli_cmd(utils.build_cmd("remove", "all", append=["--volume", "--network"]))


@pytest.fixture
def start_docker() -> None:
    """
    Start the Docker daemon.

    Notes
    -----
    Runs before the test.
    """
    common.start_docker_daemon()
    yield


@pytest.fixture
def stop_docker() -> None:
    """
    Stop the Docker daemon.

    Notes
    -----
    Runs before the test.
    """
    common.stop_docker_daemon()
    yield


@pytest.fixture
def cleanup_config(logger: logging.Logger) -> None:
    """
    Ensure a sample config file and directory exist.

    Parameters
    ----------
    logger : logging.Logger
        The logger instance.

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
def cleanup_snapshot(request: pytest.FixtureRequest, logger: logging.Logger) -> None:
    """
    Remove test snapshot tarball.

    Parameters
    ----------
    request : pytest.FixtureRequest
        The pytest fixture request.
    logger : logging.Logger
        The logger instance.

    Notes
    -----
    Runs before and after the test.
    """
    snapshot_name = getattr(request, "param", "test")

    def rm_snapshot():
        try:
            if snapshot_name != "test":
                path = os.path.join(
                    MINITRINO_USER_SNAPSHOTS_DIR, snapshot_name + ".tar.gz"
                )
                if os.path.isfile(path):
                    logger.debug(f"Removing snapshot file: {path}")
                    os.remove(path)
                else:
                    logger.debug(f"Snapshot file does not exist: {path}")
            else:
                if os.path.isfile(SNAPSHOT_FILE):
                    logger.debug(f"Removing default snapshot file: {SNAPSHOT_FILE}")
                    os.remove(SNAPSHOT_FILE)
                else:
                    logger.debug(
                        f"Default snapshot file does not exist: {SNAPSHOT_FILE}"
                    )
        except Exception as e:
            logger.error(f"Error cleaning up snapshot file: {e}")
            raise RuntimeError(f"Error cleaning up snapshot file: {e}")

    logger.debug("Running snapshot cleanup (before test)")
    rm_snapshot()
    yield
    logger.debug("Running snapshot cleanup (after test)")
    rm_snapshot()


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
    Module defaults to `test` if not specified. Runs after the test.
    """
    yield
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
    utils.write_file(path, json.dumps(default, indent=2))


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
    Shuts down the clusters after creation unless `keepalive` is set to `True`.
    """
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
        utils.cli_cmd(utils.build_cmd("provision", cluster, append=module_flags))

    if not keepalive:
        down_cluster = "all" if len(cluster_names) > 1 else cluster_names[0]
        utils.cli_cmd(utils.build_cmd("down", down_cluster, append=["--sig-kill"]))
    yield


@pytest.fixture(scope="session")
def dummy_resources(logger: logging.Logger) -> dict:
    """
    Spin up dummy Docker resources for testing.

    Parameters
    ----------
    logger : logging.Logger
        The logger instance.

    Returns
    -------
    dict
        Dictionary of created resource objects.

    Notes
    -----
    Fails if resource cleanup fails. Logs resource creation and cleanup.
    """
    logger.info("Starting Docker daemon for dummy resources")
    common.start_docker_daemon()
    client = docker.from_env()
    resources = {}
    volume = "minitrino_dummy_volume"
    image = "minitrino_dummy_image"
    network = "minitrino_dummy_network"
    container = "minitrino_dummy_container"
    labels = {"org.minitrino": "test"}

    logger.info(f"Creating dummy volume: {volume}")
    resources["volume"] = client.volumes.create(name=volume, labels=labels)
    logger.info("Pulling busybox:latest image")
    client.images.pull("busybox:latest")
    dockerfile = "FROM busybox:latest\n\nLABEL org.minitrino=test"
    logger.info(f"Building dummy image: {image}")
    image_obj, _ = client.images.build(
        fileobj=io.BytesIO(dockerfile.encode()), tag=image, rm=True
    )
    resources["image"] = image_obj
    logger.info(f"Creating dummy network: {network}")
    resources["network"] = client.networks.create(network, labels=labels)
    logger.info(f"Creating dummy container: {container}")
    resources["container"] = client.containers.create(
        image=image,
        name=container,
        command="sleep 60000",
        detach=True,
        network=network,
        labels=labels,
    )

    yield resources

    errors = []
    c = client.containers
    remove = [
        ("container", container, lambda: c.get(container).remove(force=True)),
        ("volume", volume, lambda: client.volumes.get(volume).remove(force=True)),
        ("network", network, lambda: client.networks.get(network).remove()),
        ("image", image, lambda: client.images.remove(image, force=True)),
    ]
    for resource_type, name, action in remove:
        try:
            action()
            logger.info(f"Removed {resource_type}: {name}")
        except Exception as e:
            logger.error(f"Failed to remove {resource_type} {name}: {e}")
            errors.append(f"Failed to remove {resource_type} {name}: {e}")
    if errors:
        raise RuntimeError("\n".join(errors))
