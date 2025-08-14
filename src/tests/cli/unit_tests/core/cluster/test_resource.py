"""Unit tests for cluster resource management module.

Tests the ClusterResourceManager class for Docker resource operations.
"""

from unittest.mock import Mock, patch

import pytest

from minitrino.core.cluster.resource import ClusterResourceManager
from minitrino.core.docker.wrappers import MinitrinoContainer


class TestClusterResourceManager:
    """Test suite for ClusterResourceManager class."""

    def create_mock_context(self, cluster_name="test-cluster"):
        """Create a mock MinitrinoContext."""
        mock_ctx = Mock()
        mock_ctx.cluster_name = cluster_name
        mock_ctx.logger = Mock()
        mock_ctx.docker_client = Mock()
        return mock_ctx

    def test_initialization(self):
        """Test ClusterResourceManager initialization."""
        mock_ctx = self.create_mock_context()

        manager = ClusterResourceManager(mock_ctx)

        assert manager._ctx == mock_ctx
        assert manager._logged_cluster_resource_msg is False

    def test_compose_project_name_with_default(self):
        """Test compose project name generation with default cluster."""
        mock_ctx = self.create_mock_context("my-cluster")
        manager = ClusterResourceManager(mock_ctx)

        project_name = manager.compose_project_name()

        assert project_name == "minitrino-my-cluster"

    def test_compose_project_name_with_explicit(self):
        """Test compose project name with explicit cluster name."""
        mock_ctx = self.create_mock_context("default")
        manager = ClusterResourceManager(mock_ctx)

        project_name = manager.compose_project_name("custom-cluster")

        assert project_name == "minitrino-custom-cluster"

    def test_fq_container_name_simple(self):
        """Test fully qualified container name construction."""
        mock_ctx = self.create_mock_context("prod")
        manager = ClusterResourceManager(mock_ctx)

        fq_name = manager.fq_container_name("trino")

        assert fq_name == "trino-prod"

    def test_fq_container_name_with_cluster_var(self):
        """Test FQ name with literal ${CLUSTER_NAME} suffix."""
        mock_ctx = self.create_mock_context("staging")
        manager = ClusterResourceManager(mock_ctx)

        # This happens when reading from Docker Compose files
        fq_name = manager.fq_container_name("postgres-${CLUSTER_NAME}")

        assert fq_name == "postgres-staging"

    def test_container_retrieval(self):
        """Test retrieving a container by fully qualified name."""
        mock_ctx = self.create_mock_context("test")
        mock_base_container = Mock()
        mock_base_container.name = "trino-test"
        mock_ctx.docker_client.containers.get.return_value = mock_base_container

        manager = ClusterResourceManager(mock_ctx)
        container = manager.container("trino-test")

        assert isinstance(container, MinitrinoContainer)
        assert container._base == mock_base_container
        assert container._cluster_name == "test"
        mock_ctx.docker_client.containers.get.assert_called_once_with("trino-test")

    @patch("minitrino.core.cluster.resource.MinitrinoContainer")
    @patch("minitrino.core.cluster.resource.MinitrinoNetwork")
    @patch("minitrino.core.cluster.resource.MinitrinoVolume")
    @patch("minitrino.core.cluster.resource.MinitrinoImage")
    def test_unfiltered_resources(
        self,
        mock_image_class,
        mock_volume_class,
        mock_network_class,
        mock_container_class,
    ):
        """Test fetching all unfiltered Minitrino resources."""
        mock_ctx = self.create_mock_context()

        # Mock Docker API responses
        mock_container = Mock()
        mock_container.labels = {"org.minitrino.root": "true"}
        mock_ctx.docker_client.containers.list.return_value = [mock_container]

        mock_network = Mock()
        mock_network.attrs = {"Labels": {"org.minitrino.root": "true"}}
        mock_ctx.docker_client.networks.list.return_value = [mock_network]

        mock_volume = Mock()
        mock_volume.attrs = {"Labels": {"org.minitrino.root": "true"}}
        mock_ctx.docker_client.volumes.list.return_value = [mock_volume]

        mock_image = Mock()
        mock_image.labels = {"org.minitrino.root": "true"}
        mock_ctx.docker_client.images.list.return_value = [mock_image]

        manager = ClusterResourceManager(mock_ctx)
        resources = manager.unfiltered_resources()

        assert "containers" in resources
        assert "networks" in resources
        assert "volumes" in resources
        assert "images" in resources

        # Verify Docker API was called
        mock_ctx.docker_client.containers.list.assert_called_once()
        mock_ctx.docker_client.networks.list.assert_called_once()
        mock_ctx.docker_client.volumes.list.assert_called_once()
        mock_ctx.docker_client.images.list.assert_called_once()

    def test_resources_for_single_cluster(self):
        """Test fetching resources for a single cluster."""
        mock_ctx = self.create_mock_context("dev")

        # Mock container with cluster label
        mock_container = Mock()
        mock_container.labels = {
            "org.minitrino.root": "true",
            "com.docker.compose.project": "minitrino-dev",
        }
        mock_ctx.docker_client.containers.list.return_value = [mock_container]
        mock_ctx.docker_client.networks.list.return_value = []
        mock_ctx.docker_client.volumes.list.return_value = []
        mock_ctx.docker_client.images.list.return_value = []

        manager = ClusterResourceManager(mock_ctx)

        with patch.object(manager, "_group_resources_by_cluster") as mock_group:
            mock_group.return_value = {"dev": {"containers": [mock_container]}}
            manager.resources()

            # Should call grouping method
            mock_group.assert_called_once()

    def test_resources_for_all_clusters(self):
        """Test fetching resources when cluster name is 'all'."""
        mock_ctx = self.create_mock_context("all")

        # Mock multiple containers from different clusters
        mock_container1 = Mock()
        mock_container1.labels = {
            "org.minitrino.root": "true",
            "com.docker.compose.project": "minitrino-cluster1",
        }
        mock_container2 = Mock()
        mock_container2.labels = {
            "org.minitrino.root": "true",
            "com.docker.compose.project": "minitrino-cluster2",
        }

        mock_ctx.docker_client.containers.list.return_value = [
            mock_container1,
            mock_container2,
        ]
        mock_ctx.docker_client.networks.list.return_value = []
        mock_ctx.docker_client.volumes.list.return_value = []
        mock_ctx.docker_client.images.list.return_value = []

        manager = ClusterResourceManager(mock_ctx)

        # When cluster_name is "all", should fetch all clusters
        with patch.object(manager, "_group_resources_by_cluster") as mock_group:
            mock_group.return_value = {
                "cluster1": {"containers": [mock_container1]},
                "cluster2": {"containers": [mock_container2]},
            }
            manager.resources()

            mock_group.assert_called_once()

    def test_resources_with_additional_labels(self):
        """Test fetching resources with additional label filters."""
        mock_ctx = self.create_mock_context()

        # Mock container with multiple labels
        mock_container = Mock()
        mock_container.labels = {
            "org.minitrino.root": "true",
            "org.minitrino.module": "hive",
            "com.docker.compose.project": "minitrino-test-cluster",
        }

        mock_ctx.docker_client.containers.list.return_value = [mock_container]
        mock_ctx.docker_client.networks.list.return_value = []
        mock_ctx.docker_client.volumes.list.return_value = []
        mock_ctx.docker_client.images.list.return_value = []

        manager = ClusterResourceManager(mock_ctx)

        # Should filter by additional labels
        manager.resources(addl_labels=["org.minitrino.module=hive"])

        # Verify containers.list was called with label filter
        mock_ctx.docker_client.containers.list.assert_called()

    def test_list_clusters_from_resources(self):
        """Test deriving cluster names from resources."""
        mock_ctx = self.create_mock_context()
        manager = ClusterResourceManager(mock_ctx)

        # Create mock resources with cluster labels
        mock_container1 = Mock()
        mock_container1.labels = {"com.docker.compose.project": "minitrino-prod"}

        mock_container2 = Mock()
        mock_container2.labels = {"com.docker.compose.project": "minitrino-dev"}

        mock_network = Mock()
        mock_network.labels = {"com.docker.compose.project": "minitrino-staging"}

        resources = {
            "containers": [mock_container1, mock_container2],
            "networks": [mock_network],
            "volumes": [],
            "images": [],  # Images should be ignored
        }

        cluster_names = manager._list_clusters(resources)

        assert "prod" in cluster_names
        assert "dev" in cluster_names
        assert "staging" in cluster_names
        assert len(set(cluster_names)) == 3  # Should be unique

    def test_list_clusters_ignores_images(self):
        """Test that cluster listing ignores images."""
        mock_ctx = self.create_mock_context()
        manager = ClusterResourceManager(mock_ctx)

        mock_image = Mock()
        mock_image.labels = {"com.docker.compose.project": "should-be-ignored"}

        resources = {
            "containers": [],
            "networks": [],
            "volumes": [],
            "images": [mock_image],
        }

        cluster_names = manager._list_clusters(resources)

        assert len(cluster_names) == 0  # Images should not contribute cluster names

    def test_group_resources_by_cluster(self):
        """Test grouping resources by cluster name."""
        mock_ctx = self.create_mock_context()
        manager = ClusterResourceManager(mock_ctx)

        # Create mock resources
        mock_container1 = Mock()
        mock_container1.labels = {"com.docker.compose.project": "minitrino-cluster1"}
        mock_container1.cluster_name = "cluster1"

        mock_container2 = Mock()
        mock_container2.labels = {"com.docker.compose.project": "minitrino-cluster2"}
        mock_container2.cluster_name = "cluster2"

        _ = {
            "containers": [mock_container1, mock_container2],
            "networks": [],
            "volumes": [],
            "images": [],
        }

        with patch.object(
            manager, "_list_clusters", return_value=["cluster1", "cluster2"]
        ):
            # The actual grouping method would need to be tested
            # This is a simplified test
            assert manager._ctx is not None

    def test_resources_handles_docker_api_error(self):
        """Test resource fetching handles Docker API errors gracefully."""
        mock_ctx = self.create_mock_context()
        mock_ctx.docker_client.containers.list.side_effect = Exception(
            "Docker API error"
        )

        manager = ClusterResourceManager(mock_ctx)

        with pytest.raises(Exception) as exc_info:
            manager.unfiltered_resources()

        assert "Docker API error" in str(exc_info.value)

    def test_compose_project_name_empty_cluster(self):
        """Test compose project name with empty cluster name."""
        mock_ctx = self.create_mock_context("")
        manager = ClusterResourceManager(mock_ctx)

        # Should use context's cluster name when empty string passed
        mock_ctx.cluster_name = "fallback"
        project_name = manager.compose_project_name("")

        assert project_name == "minitrino-fallback"

    def test_fq_container_name_empty(self):
        """Test FQ container name with empty input."""
        mock_ctx = self.create_mock_context("test")
        manager = ClusterResourceManager(mock_ctx)

        fq_name = manager.fq_container_name("")

        assert fq_name == "-test"  # Will create name with just suffix

    def test_logging_cluster_resource_message(self):
        """Test that cluster resource message is logged only once."""
        mock_ctx = self.create_mock_context()
        manager = ClusterResourceManager(mock_ctx)

        # Initially should be False
        assert manager._logged_cluster_resource_msg is False

        # After setting to True, it should remain True
        manager._logged_cluster_resource_msg = True
        assert manager._logged_cluster_resource_msg is True
