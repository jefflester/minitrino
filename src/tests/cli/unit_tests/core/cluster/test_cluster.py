"""Unit tests for the main Cluster class.

Tests the Cluster class which orchestrates cluster operations.
"""

from unittest.mock import Mock, patch

from minitrino.core.cluster.cluster import Cluster


class TestCluster:
    """Test suite for Cluster class."""

    def create_mock_context(self):
        """Create a mock MinitrinoContext."""
        mock_ctx = Mock()
        mock_ctx.cluster_name = "test-cluster"
        mock_ctx.logger = Mock()
        return mock_ctx

    @patch("minitrino.core.cluster.cluster.ClusterValidator")
    @patch("minitrino.core.cluster.cluster.ClusterResourceManager")
    @patch("minitrino.core.cluster.cluster.ClusterPortManager")
    @patch("minitrino.core.cluster.cluster.ClusterOperations")
    def test_cluster_initialization(
        self,
        mock_ops_class,
        mock_ports_class,
        mock_resource_class,
        mock_validator_class,
    ):
        """Test Cluster initialization creates all managers."""
        mock_ctx = self.create_mock_context()

        # Create mock instances
        mock_ops = Mock()
        mock_ports = Mock()
        mock_resource = Mock()
        mock_validator = Mock()

        # Configure the mock classes to return our mock instances
        mock_ops_class.return_value = mock_ops
        mock_ports_class.return_value = mock_ports
        mock_resource_class.return_value = mock_resource
        mock_validator_class.return_value = mock_validator

        cluster = Cluster(mock_ctx)

        # Verify all managers were created with correct parameters
        mock_ops_class.assert_called_once_with(mock_ctx, cluster)
        mock_ports_class.assert_called_once_with(mock_ctx, cluster)
        mock_resource_class.assert_called_once_with(mock_ctx)
        mock_validator_class.assert_called_once_with(mock_ctx, cluster)

        # Verify they are accessible as attributes
        assert cluster.ops == mock_ops
        assert cluster.ports == mock_ports
        assert cluster.resource == mock_resource
        assert cluster.validator == mock_validator
        assert cluster._ctx == mock_ctx

    def test_cluster_has_context(self):
        """Test that Cluster stores the context."""
        mock_ctx = self.create_mock_context()

        with (
            patch("minitrino.core.cluster.cluster.ClusterOperations"),
            patch("minitrino.core.cluster.cluster.ClusterPortManager"),
            patch("minitrino.core.cluster.cluster.ClusterResourceManager"),
            patch("minitrino.core.cluster.cluster.ClusterValidator"),
        ):
            cluster = Cluster(mock_ctx)

        assert cluster._ctx == mock_ctx

    @patch("minitrino.core.cluster.cluster.ClusterValidator")
    @patch("minitrino.core.cluster.cluster.ClusterResourceManager")
    @patch("minitrino.core.cluster.cluster.ClusterPortManager")
    @patch("minitrino.core.cluster.cluster.ClusterOperations")
    def test_cluster_provides_interface_to_managers(
        self,
        mock_ops_class,
        mock_ports_class,
        mock_resource_class,
        mock_validator_class,
    ):
        """Test that Cluster provides access to all manager classes."""
        mock_ctx = self.create_mock_context()

        cluster = Cluster(mock_ctx)

        # Check that all expected attributes exist
        assert hasattr(cluster, "ops")
        assert hasattr(cluster, "ports")
        assert hasattr(cluster, "resource")
        assert hasattr(cluster, "validator")
        assert hasattr(cluster, "_ctx")

        # Verify they are the right types (mocked versions)
        assert mock_ops_class.called
        assert mock_ports_class.called
        assert mock_resource_class.called
        assert mock_validator_class.called
