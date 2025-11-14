"""Minitrino resource management.

This module provides classes and functions to manage Docker resources
(containers, volumes, images, networks). All Docker objects are
associated with a cluster name **except** for images, which are global.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union

from docker.models.containers import Container
from docker.models.images import Image
from docker.models.networks import Network
from docker.models.volumes import Volume

from minitrino.settings import COMPOSE_LABEL_KEY


class MinitrinoDockerObjectMixin(ABC):
    """
    Abstract base mixin for Minitrino Docker objects.

    Parameters
    ----------
    cluster_name : Optional[str]
        The name of the cluster this Docker object belongs to.
    """

    def __init__(self, cluster_name: Optional[str] = None):
        self._cluster_name = cluster_name

    @property
    def cluster_name(self) -> Optional[str]:
        """Return the cluster name associated with this object."""
        return self._cluster_name

    def __repr__(self):
        """Return a string representation of the object."""
        # Try to show name if available, else just id
        name = getattr(self, "name", None)
        if name and name != "<unknown>":
            return (
                f"<{self.kind} name={name} id={self.id} cluster={self._cluster_name}>"
            )
        return f"<{self.kind} id={self.id} cluster={self._cluster_name}>"

    @property
    def labels(self) -> dict[str, str]:
        """Retrieve Docker labels from the underlying Docker object."""
        base = getattr(self, "_base", None)
        if base is None:
            return getattr(self, "labels", {}) or {}
        attrs = getattr(base, "attrs", None)
        if isinstance(attrs, dict):
            if isinstance(self, MinitrinoContainer) and "Config" in attrs:
                return attrs["Config"].get("Labels", {}) or {}
            return attrs.get("Labels", {}) or {}
        return getattr(base, "labels", {}) or {}

    @property
    @abstractmethod
    def id(self) -> str:
        """
        The unique identifier of the Docker object.

        Returns
        -------
        str
            The object ID string.
        """
        pass

    @property
    @abstractmethod
    def kind(self) -> str:
        """
        The kind of the Docker object.

        Returns
        -------
        str
            The string identifier of the object kind (e.g.,
            "container").
        """
        pass


class MinitrinoContainer(MinitrinoDockerObjectMixin, Container):
    """
    Minitrino-wrapped container object.

    Parameters
    ----------
    base : Container
        The base Docker container to wrap.
    cluster_name : str
        The name of the cluster this container belongs to.
    """

    def __init__(self, base: Container, cluster_name: Optional[str] = None):
        super().__init__(cluster_name)
        self._base = base
        self.__dict__.update(base.__dict__)

    @property
    def id(self) -> str:
        """ID of the container."""
        return str(getattr(self._base, "id", "<unknown>") or "<unknown>")

    @property
    def name(self) -> str:
        """Name of the container."""
        return str(getattr(self._base, "name", "<unknown>") or "<unknown>")

    @property
    def kind(self) -> str:
        """Kind of object."""
        return "container"

    @property
    def cluster_name(self) -> str:
        """Cluster name associated with the container."""
        from minitrino.settings import COMPOSE_LABEL_KEY

        labels = self.labels
        project = labels.get(COMPOSE_LABEL_KEY) if labels else None
        if project and project.startswith("minitrino-"):
            return project.split("minitrino-")[1]
        return str(getattr(self, "_cluster_name", None)) or str(super().cluster_name)

    def ports_and_host_endpoints(self) -> tuple[list[str], list[str]]:
        """
        Get published and exposed ports and host endpoints.

        Returns
        -------
        tuple[list[str], list[str]]
            - ports: Published ports as 'host_port:container_port',
              exposed-only as 'container_port'
            - host_endpoints: Published host endpoints as
              'localhost:host_port'
        """
        ports_dict = self.attrs.get("NetworkSettings", {}).get("Ports", {})
        exposed_ports_dict = self.attrs.get("Config", {}).get("ExposedPorts", {})
        port_mappings = set()
        host_endpoints = set()
        published_container_ports = set()

        # Published ports
        for container_port, mappings in (ports_dict or {}).items():
            port_num = (
                container_port.split("/")[0]
                if "/" in container_port
                else container_port
            )
            if mappings:
                for mapping in mappings:
                    host_port = mapping.get("HostPort")
                    if host_port:
                        port_mappings.add(f"{host_port}:{port_num}")
                        host_endpoints.add(f"localhost:{host_port}")
                        published_container_ports.add(port_num)

        # Exposed-only ports (not published)
        for exposed_port in exposed_ports_dict or {}:
            port_num = (
                exposed_port.split("/")[0] if "/" in exposed_port else exposed_port
            )
            if port_num not in published_container_ports:
                port_mappings.add(f"{port_num}")

        return (
            sorted(port_mappings, key=lambda x: (x.count(":"), x)),
            sorted(host_endpoints),
        )


class MinitrinoVolume(MinitrinoDockerObjectMixin, Volume):
    """
    Minitrino-wrapped volume object.

    Parameters
    ----------
    base : Volume
        The base Docker volume to wrap.
    cluster_name : str
        The name of the cluster this volume belongs to.
    """

    def __init__(self, base: Volume, cluster_name: Optional[str] = None):
        super().__init__(cluster_name)
        self._base = base
        self.__dict__.update(base.__dict__)

    @property
    def id(self) -> str:
        """ID of the volume."""
        return str(getattr(self._base, "id", "<unknown>") or "<unknown>")

    @property
    def name(self) -> str:
        """Name of the volume."""
        return str(getattr(self._base, "name", "<unknown>") or "<unknown>")

    @property
    def kind(self) -> str:
        """Kind of object."""
        return "volume"

    @property
    def cluster_name(self) -> str:
        """Cluster name associated with the volume."""
        from minitrino.settings import COMPOSE_LABEL_KEY

        labels = self.labels
        project = labels.get(COMPOSE_LABEL_KEY) if labels else None
        if project and project.startswith("minitrino-"):
            return project.split("minitrino-")[1]
        return str(getattr(self, "_cluster_name", None)) or str(super().cluster_name)


class MinitrinoNetwork(MinitrinoDockerObjectMixin, Network):
    """
    Minitrino-wrapped network object.

    Parameters
    ----------
    base : Network
        The base Docker network to wrap.
    cluster_name : str
        The name of the cluster this network belongs to.
    """

    def __init__(self, base: Network, cluster_name: Optional[str] = None):
        super().__init__(cluster_name)
        self._base = base
        self.__dict__.update(base.__dict__)

    @property
    def id(self) -> str:
        """ID of the network."""
        return str(getattr(self._base, "id", "<unknown>") or "<unknown>")

    @property
    def name(self) -> str:
        """Name of the network."""
        return str(getattr(self._base, "name", "<unknown>") or "<unknown>")

    @property
    def kind(self) -> str:
        """Kind of object."""
        return "network"

    @property
    def cluster_name(self) -> str:
        """Cluster name associated with the network."""
        labels = self.labels
        project = labels.get(COMPOSE_LABEL_KEY) if labels else None
        if project and project.startswith("minitrino-"):
            return project.split("minitrino-")[1]
        return str(getattr(self, "_cluster_name", None)) or str(super().cluster_name)


class MinitrinoImage(MinitrinoDockerObjectMixin, Image):
    """
    Minitrino-wrapped image object.

    Unlike other Docker resources, images are global and not tied to a
    specific cluster. For consistency, they are assigned a special
    cluster name: "images".

    Parameters
    ----------
    base : Image
        The base Docker image to wrap.
    """

    def __init__(self, base: Image):
        MinitrinoDockerObjectMixin.__init__(self, "images")
        self._base = base
        self.__dict__.update(base.__dict__)

    @property
    def id(self) -> str:
        """ID of the image."""
        return getattr(self._base, "id", "<unknown>")

    @property
    def name(self) -> str:
        """Name of the image."""
        # Images may not always have a 'name', but try tags or repo
        tags = getattr(self._base, "tags", None)
        if tags and len(tags) > 0:
            return tags[0]
        return getattr(self._base, "short_id", "<unknown>")

    @property
    def kind(self) -> str:
        """Kind of object."""
        return "image"

    @property
    def cluster_name(self) -> str:
        """Cluster name associated with the image (always "images")."""
        return "images"


MinitrinoDockerObject = Union[
    MinitrinoContainer, MinitrinoVolume, MinitrinoNetwork, MinitrinoImage
]
