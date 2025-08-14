"""Base classes and utilities for Minitrino unit tests.

This module provides foundational infrastructure for unit testing including:
- Base test class with common setup/teardown
- Mock context management
- Test data factories
- Assertion helpers
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from unittest.mock import Mock, patch

import docker
import pytest
from click.testing import CliRunner
from docker.models.containers import Container

from minitrino.core.cluster.cluster import Cluster
from minitrino.core.context import MinitrinoContext
from minitrino.core.logging.logger import MinitrinoLogger
from minitrino.core.modules import Modules


class MinitrinoUnitTestBase:
    """Base class for all Minitrino unit tests.

    Provides common setup/teardown, mock management, and assertion helpers.
    """

    @pytest.fixture(autouse=True)
    def setup_base(self, tmp_path):
        """Set up base test environment for all unit tests."""
        self.tmp_path = tmp_path
        self.test_cluster = "test-cluster"
        self.runner = CliRunner()

        # Reset any global state
        self._reset_global_state()

        yield

        # Cleanup
        self._cleanup()

    def _reset_global_state(self):
        """Reset any global state that might affect tests."""
        # Reset logging
        import logging

        logging.shutdown()
        import importlib

        importlib.reload(logging)

    def _cleanup(self):
        """Cleanup after test execution."""
        pass

    def create_temp_file(self, content: str, suffix: str = ".txt") -> Path:
        """Create a temporary file with given content."""
        temp_file = self.tmp_path / f"test{suffix}"
        temp_file.write_text(content)
        return temp_file

    def create_temp_dir(self, name: str = "testdir") -> Path:
        """Create a temporary directory."""
        temp_dir = self.tmp_path / name
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir


class MockMinitrinoContext:
    """Mock MinitrinoContext for isolated unit testing.

    Provides configurable mocks for all context components.
    """

    def __init__(
        self,
        cluster: Optional[str] = "test",
        env: Optional[Dict[str, str]] = None,
        modules: Optional[List[str]] = None,
        verbose: bool = False,
        lib_dir: Optional[Path] = None,
    ):
        """Initialize mock context with configurable components."""
        self.cluster_name = cluster
        self.env = env or {}  # Just use a plain dict for mocking
        self.verbose = verbose
        self.lib_dir = lib_dir or Path("/tmp/minitrino-lib")

        # Create mocks for all components
        self.logger = self._create_mock_logger()
        self.docker_client = self._create_mock_docker_client()
        self.cluster = self._create_mock_cluster()
        self.modules = self._create_mock_modules(modules or [])

    def _create_mock_logger(self) -> Mock:
        """Create a mock logger with all necessary methods."""
        logger = Mock(spec=MinitrinoLogger)
        logger.info = Mock()
        logger.warn = Mock()
        logger.error = Mock()
        logger.debug = Mock()
        logger.spinner = Mock()
        logger.spinner_success = Mock()
        logger.spinner_fail = Mock()
        return logger

    def _create_mock_docker_client(self) -> Mock:
        """Create a mock Docker client."""
        client = Mock(spec=docker.DockerClient)
        client.api = Mock()
        client.containers = Mock()
        client.networks = Mock()
        client.volumes = Mock()
        client.close = Mock()
        return client

    def _create_mock_cluster(self) -> Mock:
        """Create a mock cluster."""
        cluster = Mock(spec=Cluster)
        cluster.name = self.cluster_name
        cluster.cluster_name = self.cluster_name
        cluster.containers = []
        cluster.get_containers = Mock(return_value=[])
        cluster.get_container = Mock(return_value=None)
        return cluster

    def _create_mock_modules(self, module_names: List[str]) -> Mock:
        """Create mock modules object."""
        modules = Mock(spec=Modules)
        modules.module_names = module_names
        modules.get_modules = Mock(return_value=module_names)
        modules.get_module = Mock()
        modules.validate_modules = Mock()
        return modules

    def as_context(self) -> Mock:
        """Convert to mock MinitrinoContext with mocked components."""
        ctx = Mock(spec=MinitrinoContext)
        ctx.cluster_name = self.cluster_name
        ctx.env = self.env
        ctx.verbose = self.verbose
        ctx.lib_dir = self.lib_dir
        ctx._logger = self.logger
        ctx._docker_client = self.docker_client
        ctx._cluster = self.cluster
        ctx._modules = self.modules
        ctx.logger = self.logger
        ctx.docker_client = self.docker_client
        ctx.cluster = self.cluster
        ctx.modules = self.modules
        return ctx


@dataclass
class ModuleMetadata:
    """Test data for module metadata."""

    name: str
    description: str = "Test module"
    dependencies: List[str] = field(default_factory=list)
    incompatibilities: List[str] = field(default_factory=list)
    enterprise: bool = False
    compose_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        data = {
            "description": self.description,
            "dependencies": self.dependencies,
            "incompatibilities": self.incompatibilities,
            "enterprise": self.enterprise,
        }
        if self.compose_file:
            data["compose_file"] = self.compose_file
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class TestDataFactory:
    """Factory for generating test data."""

    @staticmethod
    def create_module_metadata(name: str = "test-module", **kwargs) -> ModuleMetadata:
        """Create module metadata for testing."""
        return ModuleMetadata(name=name, **kwargs)

    @staticmethod
    def create_environment_variables(
        base_env: Optional[Dict[str, str]] = None, **kwargs
    ) -> Dict[str, str]:
        """Create environment variables dict for testing."""
        env = base_env or {}
        env.update(kwargs)
        # Convert all values to strings like EnvironmentVariables would
        return {k: str(v) for k, v in env.items()}

    @staticmethod
    def create_mock_container(
        name: str = "test-container",
        status: str = "running",
        labels: Optional[Dict[str, str]] = None,
    ) -> Mock:
        """Create a mock Docker container."""
        container = Mock(spec=Container)
        container.name = name
        container.status = status
        container.labels = labels or {"org.minitrino.cluster": "test"}
        container.attrs = {
            "State": {"Status": status},
            "Config": {"Labels": container.labels},
        }
        container.exec_run = Mock()
        container.logs = Mock(return_value=b"test logs")
        container.reload = Mock()
        return container

    @staticmethod
    def create_docker_compose_yaml(services: List[str]) -> str:
        """Create a minimal Docker Compose YAML for testing."""
        yaml_content = "version: '3.8'\nservices:\n"
        for service in services:
            yaml_content += f"  {service}:\n    image: test/{service}:latest\n"
        return yaml_content

    @staticmethod
    def create_cluster_config(
        cluster_name: str = "test",
        modules: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a cluster configuration for testing."""
        return {
            "cluster": cluster_name,
            "modules": modules or [],
            "env": env or {},
        }


class MinitrinoAssertions:
    """Common assertion helpers for Minitrino unit tests."""

    @staticmethod
    def assert_valid_cluster_state(
        cluster: Cluster,
        expected_name: str,
        expected_containers: Optional[List[str]] = None,
    ):
        """Assert that cluster is in valid state."""
        assert cluster.name == expected_name
        assert cluster.cluster_name == expected_name

        if expected_containers:
            container_names = [c.name for c in cluster.get_containers()]
            for expected in expected_containers:
                assert any(expected in name for name in container_names)

    @staticmethod
    def assert_error_type(
        func: Any,  # Using Any since Callable requires parameters
        error_class: Type[Exception],
        message_pattern: Optional[str] = None,
    ):
        """Assert that function raises expected error type."""
        with pytest.raises(error_class) as exc_info:
            func()

        if message_pattern:
            assert message_pattern in str(exc_info.value)

    @staticmethod
    def assert_log_contains(
        logger_mock: Mock,
        level: str,
        message: str,
    ):
        """Assert that logger was called with expected message."""
        method = getattr(logger_mock, level)
        calls = method.call_args_list
        assert any(
            message in str(call) for call in calls
        ), f"Expected '{message}' in {level} logs, got: {calls}"

    @staticmethod
    def assert_env_var_set(
        env: Dict[str, str],
        key: str,
        expected_value: str,
    ):
        """Assert that environment variable is set correctly."""
        assert key in env
        assert env[key] == expected_value

    @staticmethod
    def assert_module_valid(
        module_metadata: Dict[str, Any],
        expected_name: str,
    ):
        """Assert that module metadata is valid."""
        assert "description" in module_metadata
        assert isinstance(module_metadata.get("dependencies", []), list)
        assert isinstance(module_metadata.get("incompatibilities", []), list)
        assert isinstance(module_metadata.get("enterprise", False), bool)


class MockPatcher:
    """Context manager for managing multiple patches in tests."""

    def __init__(self):
        """Initialize the patcher."""
        self.patches = []

    def add(self, target: str, **kwargs) -> Mock:
        """Add a patch and return the mock."""
        patcher = patch(target, **kwargs)
        mock = patcher.start()
        self.patches.append(patcher)
        return mock

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and stop all patches."""
        for patcher in reversed(self.patches):
            patcher.stop()


# Pytest fixtures that can be used across all unit tests
@pytest.fixture
def mock_context():
    """Provide a mock MinitrinoContext."""
    return MockMinitrinoContext()


@pytest.fixture
def test_factory():
    """Provide a TestDataFactory instance."""
    return TestDataFactory()


@pytest.fixture
def assertions():
    """Provide MinitrinoAssertions helpers."""
    return MinitrinoAssertions()


@pytest.fixture
def mock_docker_client():
    """Provide a mock Docker client."""
    client = Mock(spec=docker.DockerClient)
    client.api = Mock()
    client.containers = Mock()
    client.networks = Mock()
    client.volumes = Mock()
    return client
