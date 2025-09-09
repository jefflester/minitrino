"""Unit tests for Docker wrapper classes.

Tests the MinitrinoDockerObjectMixin and container wrapper classes.
"""

from unittest.mock import Mock

from minitrino.core.docker.wrappers import (
    MinitrinoContainer,
    MinitrinoImage,
    MinitrinoNetwork,
    MinitrinoVolume,
)


class TestMinitrinoContainer:
    """Test suite for MinitrinoContainer wrapper."""

    def test_container_initialization(self):
        """Test creating a MinitrinoContainer wrapper."""
        mock_container = Mock()
        mock_container.id = "container123"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_container.attrs = {"State": {"Status": "running"}}

        wrapper = MinitrinoContainer(mock_container, cluster_name="test-cluster")

        assert wrapper._base == mock_container
        assert wrapper._cluster_name == "test-cluster"
        assert wrapper.status == "running"

    def test_container_id_property(self):
        """Test container ID property."""
        mock_container = Mock()
        mock_container.id = "abc123"

        wrapper = MinitrinoContainer(mock_container)

        assert wrapper.id == "abc123"

    def test_container_id_missing(self):
        """Test container ID when base has no ID."""
        mock_container = Mock()
        mock_container.id = None

        wrapper = MinitrinoContainer(mock_container)

        assert wrapper.id == "<unknown>"

    def test_container_name_property(self):
        """Test container name property."""
        mock_container = Mock()
        mock_container.name = "my-container"

        wrapper = MinitrinoContainer(mock_container)

        assert wrapper.name == "my-container"

    def test_container_name_missing(self):
        """Test container name when base has no name."""
        mock_container = Mock()
        mock_container.name = None

        wrapper = MinitrinoContainer(mock_container)

        assert wrapper.name == "<unknown>"

    def test_container_kind_property(self):
        """Test container kind property."""
        mock_container = Mock()

        wrapper = MinitrinoContainer(mock_container)

        assert wrapper.kind == "container"

    def test_container_cluster_name_from_labels(self):
        """Test deriving cluster name from Docker labels."""
        mock_container = Mock()
        mock_container.attrs = {
            "Config": {"Labels": {"com.docker.compose.project": "minitrino-my-cluster"}}
        }

        wrapper = MinitrinoContainer(mock_container)

        assert wrapper.cluster_name == "my-cluster"

    def test_container_cluster_name_fallback(self):
        """Test cluster name fallback when not in labels."""
        mock_container = Mock()
        mock_container.attrs = {"Config": {"Labels": {}}}

        wrapper = MinitrinoContainer(mock_container, cluster_name="fallback")

        assert wrapper.cluster_name == "fallback"

    def test_container_repr_with_name(self):
        """Test string representation with name."""
        mock_container = Mock()
        mock_container.id = "abc123"
        mock_container.name = "test-container"

        wrapper = MinitrinoContainer(mock_container, cluster_name="test")

        repr_str = repr(wrapper)
        assert "<container" in repr_str
        assert "name=test-container" in repr_str
        assert "id=abc123" in repr_str
        assert "cluster=test" in repr_str

    def test_container_repr_without_name(self):
        """Test string representation without name."""
        mock_container = Mock()
        mock_container.id = "abc123"
        mock_container.name = None

        wrapper = MinitrinoContainer(mock_container, cluster_name="test")

        repr_str = repr(wrapper)
        assert "<container" in repr_str
        assert "id=abc123" in repr_str
        assert "cluster=test" in repr_str

    def test_ports_and_host_endpoints(self):
        """Test extracting ports and host endpoints."""
        mock_container = Mock()
        mock_container.attrs = {
            "NetworkSettings": {
                "Ports": {
                    "8080/tcp": [{"HostPort": "9090"}],
                    "443/tcp": None,
                }
            },
            "Config": {
                "ExposedPorts": {
                    "8080/tcp": {},
                    "443/tcp": {},
                }
            },
        }

        wrapper = MinitrinoContainer(mock_container)
        ports, endpoints = wrapper.ports_and_host_endpoints()

        assert "9090:8080" in ports
        assert "443" in ports
        assert "localhost:9090" in endpoints

    def test_ports_and_host_endpoints_empty(self):
        """Test ports extraction with no ports."""
        mock_container = Mock()
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {}},
            "Config": {"ExposedPorts": {}},
        }

        wrapper = MinitrinoContainer(mock_container)
        ports, endpoints = wrapper.ports_and_host_endpoints()

        assert len(ports) == 0
        assert len(endpoints) == 0

    def test_labels_property_from_config(self):
        """Test getting labels from container config."""
        mock_container = Mock()
        mock_container.attrs = {
            "Config": {"Labels": {"label1": "value1", "label2": "value2"}}
        }

        wrapper = MinitrinoContainer(mock_container)
        labels = wrapper.labels

        assert labels["label1"] == "value1"
        assert labels["label2"] == "value2"

    def test_labels_property_empty(self):
        """Test getting labels when none exist."""
        mock_container = Mock()
        mock_container.attrs = {}

        wrapper = MinitrinoContainer(mock_container)
        labels = wrapper.labels

        assert labels == {}


class TestMinitrinoImage:
    """Test suite for MinitrinoImage wrapper."""

    def test_image_initialization(self):
        """Test creating a MinitrinoImage wrapper."""
        mock_image = Mock()
        mock_image.id = "image123"
        mock_image.tags = ["test:latest"]
        mock_image.__dict__ = {"size": 1024}

        wrapper = MinitrinoImage(mock_image)

        assert wrapper._base == mock_image
        assert wrapper.size == 1024

    def test_image_id_property(self):
        """Test image ID property."""
        mock_image = Mock()
        mock_image.id = "sha256:abc123"

        wrapper = MinitrinoImage(mock_image)

        assert wrapper.id == "sha256:abc123"

    def test_image_kind_property(self):
        """Test image kind property."""
        mock_image = Mock()

        wrapper = MinitrinoImage(mock_image)

        assert wrapper.kind == "image"

    def test_image_cluster_name_always_images(self):
        """Test that images always have cluster name 'images'."""
        mock_image = Mock()

        wrapper = MinitrinoImage(mock_image)

        assert wrapper.cluster_name == "images"

    def test_image_labels_from_attrs(self):
        """Test getting labels from image attrs."""
        mock_image = Mock()
        mock_image.attrs = {"Labels": {"org.opencontainers.image.version": "1.0.0"}}

        wrapper = MinitrinoImage(mock_image)
        labels = wrapper.labels

        assert labels["org.opencontainers.image.version"] == "1.0.0"


class TestMinitrinoNetwork:
    """Test suite for MinitrinoNetwork wrapper."""

    def test_network_initialization(self):
        """Test creating a MinitrinoNetwork wrapper."""
        mock_network = Mock()
        mock_network.id = "network123"
        mock_network.name = "test-network"
        mock_network.__dict__ = {"driver": "bridge"}

        wrapper = MinitrinoNetwork(mock_network, cluster_name="test-cluster")

        assert wrapper._base == mock_network
        assert wrapper._cluster_name == "test-cluster"
        assert wrapper.driver == "bridge"

    def test_network_id_property(self):
        """Test network ID property."""
        mock_network = Mock()
        mock_network.id = "net456"

        wrapper = MinitrinoNetwork(mock_network)

        assert wrapper.id == "net456"

    def test_network_name_property(self):
        """Test network name property."""
        mock_network = Mock()
        mock_network.name = "my-network"

        wrapper = MinitrinoNetwork(mock_network)

        assert wrapper.name == "my-network"

    def test_network_kind_property(self):
        """Test network kind property."""
        mock_network = Mock()

        wrapper = MinitrinoNetwork(mock_network)

        assert wrapper.kind == "network"

    def test_network_cluster_name_from_labels(self):
        """Test deriving cluster name from Docker labels."""
        mock_network = Mock()
        mock_network.attrs = {
            "Labels": {"com.docker.compose.project": "minitrino-prod"}
        }

        wrapper = MinitrinoNetwork(mock_network)

        assert wrapper.cluster_name == "prod"


class TestMinitrinoVolume:
    """Test suite for MinitrinoVolume wrapper."""

    def test_volume_initialization(self):
        """Test creating a MinitrinoVolume wrapper."""
        mock_volume = Mock()
        mock_volume.id = "volume123"
        mock_volume.name = "test-volume"
        mock_volume.__dict__ = {"driver": "local"}

        wrapper = MinitrinoVolume(mock_volume, cluster_name="test-cluster")

        assert wrapper._base == mock_volume
        assert wrapper._cluster_name == "test-cluster"
        assert wrapper.driver == "local"

    def test_volume_id_property(self):
        """Test volume ID property."""
        mock_volume = Mock()
        mock_volume.id = "vol789"

        wrapper = MinitrinoVolume(mock_volume)

        assert wrapper.id == "vol789"

    def test_volume_name_property(self):
        """Test volume name property."""
        mock_volume = Mock()
        mock_volume.name = "my-volume"

        wrapper = MinitrinoVolume(mock_volume)

        assert wrapper.name == "my-volume"

    def test_volume_kind_property(self):
        """Test volume kind property."""
        mock_volume = Mock()

        wrapper = MinitrinoVolume(mock_volume)

        assert wrapper.kind == "volume"

    def test_volume_cluster_name_from_labels(self):
        """Test deriving cluster name from Docker labels."""
        mock_volume = Mock()
        mock_volume.attrs = {
            "Labels": {"com.docker.compose.project": "minitrino-staging"}
        }

        wrapper = MinitrinoVolume(mock_volume)

        assert wrapper.cluster_name == "staging"

    def test_volume_id_fallback(self):
        """Test volume ID fallback when id is None."""
        mock_volume = Mock()
        mock_volume.id = None

        wrapper = MinitrinoVolume(mock_volume)

        assert wrapper.id == "<unknown>"
