"""Minitrino resource management.

This module provides classes and functions to manage Docker resources
(containers, volumes, images, networks). All Docker objects are
associated with a cluster name **except** for images, which are global.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from minitrino.core.docker.wrappers import (
    MinitrinoContainer,
    MinitrinoDockerObject,
    MinitrinoImage,
    MinitrinoNetwork,
    MinitrinoVolume,
)
from minitrino.settings import COMPOSE_LABEL_KEY, ROOT_LABEL

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class ClusterResourceManager:
    """
    Expose cluster resources operations.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and
        context.

    Methods
    -------
    resources(addl_labels: Optional[list[str]] = None)
        Collects Docker objects (containers, volumes, images, networks)
        for the current cluster or all clusters if the context's cluster
        name is `"all"`.
    unfiltered_resources()
        Collects all Docker objects associated with Minitrino. Unlike
        the `resources()` method, this method does not group resources
        by cluster or take additional labels to filter by.
    compose_project_name(cluster_name: str = "")
        Computes the Docker Compose project name for a cluster.
    fq_container_name(container_name: str)
        Constructs a fully qualified Docker container name by appending
        the active cluster name to a base container name.
    container(fq_container_name: str)
        Retrieves a Docker container object by fully qualified name.
    """

    def __init__(self, ctx: MinitrinoContext):
        self._ctx = ctx
        self._logged_cluster_resource_msg = False

    def resources(
        self, addl_labels: Optional[list[str]] = None
    ) -> MinitrinoResourcesView:
        """
        Fetch Docker objects for the current context.

        Parameters
        ----------
        addl_labels : list[str], optional
            A list of additional labels to filter resources by. All
            Docker objects must match all labels in the list to be
            included in the result. If not provided, resource retrieval
            is limited only to the root label `ROOT_LABEL`
            (`org.minitrino.root=true`).

        Returns
        -------
        MinitrinoResourcesView
            An object that exposes grouped and typed access to resources
            by cluster and type. Images are grouped under a separate
            global key.

        Notes
        -----
        If the context's cluster name is `"all"`, resources for all
        clusters are returned.
        """
        addl_labels = addl_labels or []
        unfiltered = self.unfiltered_resources()

        clusters = (
            self._list_clusters(unfiltered)
            if self._ctx.all_clusters
            else [self._ctx.cluster_name]
        )

        grouped: dict[str, dict[str, list[MinitrinoDockerObject]]] = {}

        for cluster in clusters:
            filtered = self._filter_by_cluster(unfiltered, [cluster], addl_labels)
            filtered.pop("images", None)  # Remove "images" from the per-cluster dict
            grouped[cluster] = filtered

        # Add images as a separate key
        grouped["images"] = {"images": unfiltered.get("images", [])}

        # Flatten grouped dict into a single-level dict with keys:
        # containers, volumes, networks, images
        flat_grouped = {
            "containers": [],
            "volumes": [],
            "networks": [],
            "images": grouped.get("images", {}).get("images", []),
        }
        for cluster in clusters:
            cluster_resources = grouped.get(cluster, {})
            for key in ("containers", "volumes", "networks"):
                flat_grouped[key].extend(cluster_resources.get(key, []))
        return MinitrinoResourcesView(flat_grouped)

    def unfiltered_resources(
        self,
    ) -> dict[str, list[MinitrinoDockerObject]]:
        """
        Collect all Docker objects associated with Minitrino.

        Returns
        -------
        dict[str, list[MinitrinoDockerObject]]
            Dictionary containing the following keys and corresponding
            Docker objects.

        Examples
        --------
        >>> {
                "containers": [Container("foo"), ...],
                "volumes": [Volume("bar"), ...],
                "images": [Image("baz"), ...],
                "networks": [Network("qux"), ...],
            }

        Notes
        -----
        Unlike the `resources()` method, this method does not group
        resources by cluster or take additional labels to filter by.
        Fetch containers, volumes, images, and networks that are tagged
        with the global label `ROOT_LABEL` (`org.minitrino.root=true`).
        """
        filters = {"label": [ROOT_LABEL]}
        cluster = self._ctx.cluster_name
        return {
            "containers": [
                MinitrinoContainer(c, cluster)
                for c in self._ctx.docker_client.containers.list(
                    filters=filters, all=True
                )
            ],
            "volumes": [
                MinitrinoVolume(v, cluster)
                for v in self._ctx.docker_client.volumes.list(filters=filters)
            ],
            "images": [
                MinitrinoImage(i)
                for i in self._ctx.docker_client.images.list(filters=filters, all=True)
            ],
            "networks": [
                MinitrinoNetwork(n, cluster)
                for n in self._ctx.docker_client.networks.list(filters=filters)
            ],
        }

    def compose_project_name(self, cluster_name: str = "") -> str:
        """
        Compute the Docker Compose project name for a cluster.

        Parameters
        ----------
        cluster_name : str, optional
            A specific cluster name. If omitted, uses the current
            cluster name.

        Returns
        -------
        str
            The composed project name.
        """
        if not cluster_name:
            cluster_name = self._ctx.cluster_name
        return f"minitrino-{cluster_name}"

    def fq_container_name(self, name: str = "") -> str:
        """
        Construct and return a fully-qualified Docker container name.

        Parameters
        ----------
        name : str
            The base container name.

        Returns
        -------
        str
            Fully-qualified container name.
        """
        # If we receive a container name with a literal suffix
        # `-${CLUSTER_NAME}`, remove it. In this case, the container
        # name was sourced by reading the Docker Compose file directly,
        # which literally appends `-${CLUSTER_NAME}` to each container
        # name.
        if "-${CLUSTER_NAME}" in name:
            name = name.replace("-${CLUSTER_NAME}", "")
        return f"{name}-{self._ctx.cluster_name}"

    def container(self, fq_container_name: str = "") -> MinitrinoContainer:
        """
        Retrieve a MinitrinoContainer by fully-qualified name.

        Parameters
        ----------
        fq_container_name : str
            Fully-qualified container name to fetch.

        Returns
        -------
        MinitrinoContainer
            The matching container object, wrapped with cluster
            metadata.
        """
        base = self._ctx.docker_client.containers.get(fq_container_name)
        return MinitrinoContainer(base, self._ctx.cluster_name)

    def _list_clusters(
        self,
        resources: dict[str, list[MinitrinoDockerObject]],
    ) -> list[str]:
        """
        Derive cluster names from Docker resources.

        Parameters
        ----------
        resources : dict[str, list[MinitrinoDockerObject]]
            Dictionary containing lists of Docker objects keyed by type.

        Returns
        -------
        list[str]
            A sorted list of unique cluster names inferred from Docker
            resource labels.

        Notes
        -----
        Cluster names cannot be derived from images since they do not
        maintain a one-to-one relationship with a specific cluster.
        """
        cluster_names = []
        for obj_type, objects in resources.items():
            if obj_type == "images":
                continue
            for obj in objects:
                labels = obj.labels
                project = labels.get(COMPOSE_LABEL_KEY) if labels else None
                if project:
                    cluster_names.append(project.split("minitrino-")[1])

        cluster_names = sorted(list(set(cluster_names)))
        if not self._logged_cluster_resource_msg:
            self._ctx.logger.debug(
                f"Identified the following clusters with existing "
                f"Docker resources: {cluster_names}"
            )
            self._logged_cluster_resource_msg = True
        return cluster_names

    def _deduplicate_objects(
        self, objects: list[MinitrinoDockerObject], key: str
    ) -> list[MinitrinoDockerObject]:
        seen = set()
        result = []
        for obj in objects:
            if key == "images":
                obj_id = f"{obj.id}|{','.join(getattr(obj, 'tags', []) or [])}"
            else:
                obj_id = getattr(obj, "id", "")
            if obj_id and obj_id not in seen:
                seen.add(obj_id)
                result.append(obj)
        return result

    def _filter_by_cluster(
        self,
        resources: dict[str, list[MinitrinoDockerObject]],
        clusters: list[str],
        addl_labels: Optional[list[str]] = None,
    ) -> dict[str, list[MinitrinoDockerObject]]:
        """
        Filter resources by cluster name and optional label criteria.

        Parameters
        ----------
        resources : dict[str, list[MinitrinoDockerObject]]
            Dictionary of Docker resources categorized by type.
        clusters : list[str]
            List of cluster names to include.
        addl_labels : Optional[list[str]], optional
            Additional labels to filter resources by, by default None.

        Returns
        -------
        dict[str, list[MinitrinoDockerObject]]
            Filtered dictionary of Docker resources categorized by type.
        """
        base_labels = list(addl_labels) if addl_labels is not None else []
        if ROOT_LABEL not in base_labels:
            base_labels.append(ROOT_LABEL)

        label_filters = {}
        for label in base_labels:
            if "=" in label:
                k, v = label.split("=", 1)
                label_filters[k] = v

        filtered: dict[str, list] = {k: [] for k in resources.keys()}
        for obj_type, objects in resources.items():
            for obj in objects:
                if (  # Images are global. Cluster name does not apply.
                    obj_type != "images" and obj.cluster_name not in clusters
                ):
                    continue
                labels = obj.labels
                if not all(labels.get(k) == v for k, v in label_filters.items()):
                    continue
                filtered[obj_type].append(obj)

        for key in filtered:
            filtered[key] = self._deduplicate_objects(filtered[key], key)

        return filtered


class MinitrinoResourcesView:
    """
    Provide structured access to Docker resources grouped by type.

    Parameters
    ----------
    resources : dict[str, list[MinitrinoDockerObject]]
        A dictionary of Docker resources grouped by type.

    Notes
    -----
    This class is returned by the `resources()` method and exposes
    convenient accessors for retrieving all containers, volumes,
    networks, or images. Each object tracks its cluster internally via
    the injected `cluster_name`.
    """

    def __init__(
        self,
        resources: dict[str, list[MinitrinoDockerObject]],
    ):
        """
        Initialize a view of Docker resources grouped by type.

        Parameters
        ----------
        resources : dict[str, list[MinitrinoDockerObject]]
            Docker objects grouped by type.
        """
        self._containers: list[MinitrinoContainer] = [
            o
            for o in resources.get("containers", [])
            if isinstance(o, MinitrinoContainer)
        ]
        self._volumes: list[MinitrinoVolume] = [
            o for o in resources.get("volumes", []) if isinstance(o, MinitrinoVolume)
        ]
        self._networks: list[MinitrinoNetwork] = [
            o for o in resources.get("networks", []) if isinstance(o, MinitrinoNetwork)
        ]
        self._images: list[MinitrinoImage] = [
            o for o in resources.get("images", []) if isinstance(o, MinitrinoImage)
        ]

    def containers(self) -> list[MinitrinoContainer]:
        """
        Return a list of MinitrinoContainer objects.

        Returns
        -------
        list[MinitrinoContainer]
            List of Minitrino-wrapped Docker Container objects.
        """
        return self._containers

    def volumes(self) -> list[MinitrinoVolume]:
        """
        Return a list of MinitrinoVolume objects.

        Returns
        -------
        list[MinitrinoVolume]
            List of Minitrino-wrapped Docker Volume objects.
        """
        return self._volumes

    def networks(self) -> list[MinitrinoNetwork]:
        """
        Return a list of MinitrinoNetwork objects.

        Returns
        -------
        list[MinitrinoNetwork]
            List of Minitrino-wrapped Docker Network objects.
        """
        return self._networks

    def images(self) -> list[MinitrinoImage]:
        """
        Return a list of MinitrinoImage objects.

        Returns
        -------
        list[MinitrinoImage]
            List of Minitrino-wrapped Docker Image objects.
        """
        return self._images

    def raw(self) -> dict[str, list[MinitrinoDockerObject]]:
        """
        Return raw grouped Docker resources.

        Returns
        -------
        dict[str, list[MinitrinoDockerObject]]
            A dictionary mapping resource types to lists of Docker
            objects.
        """
        return {
            "containers": list(self._containers),
            "volumes": list(self._volumes),
            "networks": list(self._networks),
            "images": list(self._images),
        }
