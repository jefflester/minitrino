"""Shared pytest fixtures for Minitrino unit tests.

This module provides reusable fixtures for testing various Minitrino components.
Fixtures are organized by category and can be composed for complex test scenarios.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from minitrino.core.errors import MinitrinoError
from tests.cli.unit_tests.base import (
    MinitrinoAssertions,
    TestDataFactory,
)

# =============================================================================
# Context and Configuration Fixtures
# =============================================================================


@pytest.fixture
def cli_runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_minitrino_home(tmp_path):
    """Create a temporary Minitrino home directory."""
    home = tmp_path / ".minitrino"
    home.mkdir()
    (home / "minitrino.cfg").touch()
    return home


@pytest.fixture
def temp_lib_dir(tmp_path):
    """Create a temporary library directory with basic structure."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()

    # Create basic library structure
    (lib_dir / "version").write_text("3.0.0")
    (lib_dir / "docker-compose.yaml").write_text(
        "version: '3.8'\nservices:\n  minitrino:\n    image: test"
    )
    (lib_dir / "minitrino.env").write_text("STARBURST_VER=443-e.0")

    # Create module directories
    for category in ["admin", "catalog", "security"]:
        (lib_dir / "modules" / category).mkdir(parents=True)

    return lib_dir


@pytest.fixture
def mock_env():
    """Provide mock environment variables."""
    return {
        "STARBURST_VER": "443-e.0",
        "MINITRINO_LIB_DIR": "/tmp/minitrino-lib",
        "MINITRINO_CLUSTER": "test",
    }


# =============================================================================
# Docker Fixtures
# =============================================================================


@pytest.fixture
def mock_docker_api():
    """Provide a mock Docker API client."""
    api = Mock()
    api.version = Mock(return_value={"Version": "20.10.0"})
    api.ping = Mock(return_value=True)
    return api


@pytest.fixture
def mock_docker_container():
    """Provide a mock Docker container."""
    container = Mock()
    container.name = "test-container"
    container.status = "running"
    container.labels = {"org.minitrino.cluster": "test"}
    container.attrs = {
        "State": {"Status": "running", "Running": True},
        "Config": {"Labels": container.labels},
    }
    container.exec_run = Mock(return_value=(0, b"success"))
    container.logs = Mock(return_value=b"container logs")
    container.reload = Mock()
    container.remove = Mock()
    container.stop = Mock()
    return container


@pytest.fixture
def mock_docker_network():
    """Provide a mock Docker network."""
    network = Mock()
    network.name = "test-network"
    network.attrs = {"Name": "test-network"}
    network.remove = Mock()
    return network


@pytest.fixture
def mock_docker_volume():
    """Provide a mock Docker volume."""
    volume = Mock()
    volume.name = "test-volume"
    volume.attrs = {"Name": "test-volume"}
    volume.remove = Mock()
    return volume


@pytest.fixture
def mock_docker_client(mock_docker_api, mock_docker_container):
    """Provide a fully mocked Docker client."""
    client = Mock()
    client.api = mock_docker_api
    client.containers = Mock()
    client.containers.list = Mock(return_value=[mock_docker_container])
    client.containers.get = Mock(return_value=mock_docker_container)
    client.networks = Mock()
    client.networks.list = Mock(return_value=[])
    client.volumes = Mock()
    client.volumes.list = Mock(return_value=[])
    client.close = Mock()
    return client


# =============================================================================
# Module Fixtures
# =============================================================================


@pytest.fixture
def sample_module_metadata():
    """Provide sample module metadata."""
    return {
        "minio": {
            "description": "MinIO S3-compatible storage",
            "dependencies": [],
            "incompatibilities": [],
            "enterprise": False,
        },
        "hive": {
            "description": "Hive Metastore with Postgres",
            "dependencies": ["postgres"],
            "incompatibilities": [],
            "enterprise": False,
        },
        "ldap": {
            "description": "LDAP authentication",
            "dependencies": [],
            "incompatibilities": ["oauth2"],
            "enterprise": False,
        },
        "insights": {
            "description": "Starburst Insights",
            "dependencies": [],
            "incompatibilities": [],
            "enterprise": True,
        },
    }


@pytest.fixture
def module_dir_structure(tmp_path, sample_module_metadata):
    """Create a mock module directory structure."""
    modules_dir = tmp_path / "modules"

    for category in ["admin", "catalog", "security"]:
        category_dir = modules_dir / category
        category_dir.mkdir(parents=True)

    # Create actual module files
    module_paths = {
        "minio": modules_dir / "admin" / "minio",
        "hive": modules_dir / "catalog" / "hive",
        "ldap": modules_dir / "security" / "ldap",
        "insights": modules_dir / "admin" / "insights",
    }

    for name, path in module_paths.items():
        path.mkdir()
        metadata_file = path / "metadata.json"
        metadata_file.write_text(json.dumps(sample_module_metadata[name], indent=2))

        # Create module YAML file
        yaml_file = path / f"{name}.yaml"
        yaml_file.write_text(
            f"version: '3.8'\nservices:\n  {name}:\n    image: test/{name}"
        )

    return modules_dir


# =============================================================================
# Cluster Fixtures
# =============================================================================


@pytest.fixture
def mock_cluster():
    """Provide a mock cluster object."""
    cluster = Mock()
    cluster.name = "test-cluster"
    cluster.cluster_name = "test-cluster"
    cluster.containers = []
    cluster.networks = []
    cluster.volumes = []
    cluster.get_containers = Mock(return_value=[])
    cluster.get_container = Mock(return_value=None)
    cluster.is_running = Mock(return_value=False)
    return cluster


@pytest.fixture
def running_cluster(mock_cluster, mock_docker_container):
    """Provide a mock running cluster."""
    mock_cluster.containers = [mock_docker_container]
    mock_cluster.get_containers = Mock(return_value=[mock_docker_container])
    mock_cluster.is_running = Mock(return_value=True)
    return mock_cluster


# =============================================================================
# Command Execution Fixtures
# =============================================================================


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="command output",
            stderr="",
        )
        yield mock_run


@pytest.fixture
def mock_compose_cmd():
    """Mock Docker Compose command execution."""
    with patch("minitrino.core.exec.host.execute_host_cmd") as mock_exec:
        mock_exec.return_value = Mock(
            exit_code=0,
            output="Docker Compose executed successfully",
            error="",
        )
        yield mock_exec


# =============================================================================
# Logging Fixtures
# =============================================================================


@pytest.fixture
def mock_logger():
    """Provide a mock logger."""
    logger = Mock()
    logger.info = Mock()
    logger.warn = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    logger.spinner = Mock()
    logger.spinner_success = Mock()
    logger.spinner_fail = Mock()

    # Make spinner a context manager
    spinner_ctx = MagicMock()
    spinner_ctx.__enter__ = Mock(return_value=spinner_ctx)
    spinner_ctx.__exit__ = Mock(return_value=None)
    logger.spinner.return_value = spinner_ctx

    return logger


@pytest.fixture
def capture_logs():
    """Capture log messages for assertion."""
    logs = []

    def log_capture(message, level="info"):
        logs.append({"level": level, "message": message})

    return logs, log_capture


# =============================================================================
# Error Handling Fixtures
# =============================================================================


@pytest.fixture
def minitrino_error():
    """Provide a MinitrinoError for testing."""
    return MinitrinoError("Test error", exit_code=1)


@pytest.fixture
def user_error():
    """Provide a UserError for testing."""
    from minitrino.core.errors import UserError

    return UserError("User error", "Try this instead")


# =============================================================================
# Test Scenario Fixtures
# =============================================================================


@pytest.fixture
def provision_scenario():
    """Provide a standard provision test scenario."""
    return {
        "cluster": "test",
        "modules": ["minio", "hive"],
        "env": {"STARBURST_VER": "443-e.0"},
        "expected_containers": ["minitrino", "minio", "hive", "postgres"],
    }


@pytest.fixture
def complex_module_scenario():
    """Provide a complex module dependency scenario."""
    return {
        "modules": ["hive", "ldap", "minio"],
        "dependencies_resolved": ["postgres", "hive", "ldap", "minio"],
        "incompatible_with": ["oauth2"],
    }


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def assertions():
    """Provide assertion helpers."""
    return MinitrinoAssertions()


@pytest.fixture
def data_factory():
    """Provide test data factory."""
    return TestDataFactory()


@pytest.fixture
def patch_manager():
    """Provide a patch manager for multiple mocks."""
    patches = []

    def add_patch(target, **kwargs):
        p = patch(target, **kwargs)
        mock = p.start()
        patches.append(p)
        return mock

    yield add_patch

    # Cleanup all patches
    for p in reversed(patches):
        p.stop()


# =============================================================================
# Configuration File Fixtures
# =============================================================================


@pytest.fixture
def sample_config_file(tmp_path):
    """Create a sample configuration file."""
    config_file = tmp_path / "minitrino.cfg"
    config_content = """
[DEFAULT]
LIB_DIR = /opt/minitrino/lib
STARBURST_VER = 443-e.0

[test-cluster]
MINITRINO_CLUSTER = test
MINITRINO_MODULES = minio,hive
"""
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def docker_compose_file(tmp_path):
    """Create a sample Docker Compose file."""
    compose_file = tmp_path / "docker-compose.yaml"
    compose_content = """
version: '3.8'
services:
  minitrino:
    image: minitrino/minitrino:latest
    container_name: minitrino
    networks:
      - minitrino
networks:
  minitrino:
    name: minitrino
"""
    compose_file.write_text(compose_content)
    return compose_file
