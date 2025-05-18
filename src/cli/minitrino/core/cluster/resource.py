"""Cluster resource management for Minitrino.

This module provides classes and functions to manage Docker resources (containers,
volumes, images, networks) for Minitrino clusters.
"""

from __future__ import annotations

from minitrino.settings import COMPOSE_LABEL_KEY, ROOT_LABEL

from docker.models.containers import Container
from docker.models.images import Image
from docker.models.networks import Network
from docker.models.volumes import Volume
from typing import cast, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class ClusterResourceManager:
    """
    Expose cluster resources operations.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and context.

    Methods
    -------
    resources(addl_labels: Optional[list[str]] = None)
        Collects Docker objects (containers, volumes, images, networks) for the current
        cluster or all clusters if the context's cluster name is `"all"`.
    unfiltered_resources()
        Collects all Docker objects associated with Minitrino. Unlike the `resources()`
        method, this method does not group resources by cluster or take additional
        labels to filter by.
    compose_project_name(cluster_name: str = "")
        Computes the Docker Compose project name for a cluster.
    fq_container_name(container_name: str)
        Constructs a fully qualified Docker container name by appending the active
        cluster name to a base container name.
    container(fq_container_name: str)
        Retrieves a Docker container object by fully qualified name.
    """

    def __init__(self, ctx: MinitrinoContext):
        self._ctx = ctx

    def resources(
        self, addl_labels: Optional[list[str]] = None
    ) -> ClusterResourcesView:
        """
        Fetch Docker objects for the current context.

        Parameters
        ----------
        addl_labels : list[str], optional
            A list of additional labels to filter resources by. All Docker objects must
            match all labels in the list to be included in the result. If not provided,
            resource retrieval is limited only to the root label `ROOT_LABEL`
            (`org.minitrino=root`).

        Returns
        -------
        ClusterResourcesView
            An object that exposes grouped and typed access to resources by cluster and
            type. Images are grouped under a separate global key.

        Notes
        -----
        If the context's cluster name is `"all"`, resources for all clusters are
        returned.
        """
        addl_labels = addl_labels or []
        unfiltered = self.unfiltered_resources()

        clusters = (
            self._list_clusters(unfiltered)
            if self._ctx.all_clusters
            else [self._ctx.cluster_name]
        )

        grouped: dict[str, dict[str, list[Container | Volume | Network | Image]]] = {}

        for cluster in clusters:
            filtered = self._filter_by_cluster(unfiltered, [cluster], addl_labels)
            filtered.pop("images", None)  # Remove "images" from the per-cluster dict
            grouped[cluster] = filtered

        # Add images as a separate key
        grouped["images"] = {"images": unfiltered.get("images", [])}

        return ClusterResourcesView(grouped)

    def unfiltered_resources(
        self,
    ) -> dict[str, list[Container | Volume | Image | Network]]:
        """
        Collect all Docker objects associated with Minitrino.

        Returns
        -------
        dict[str, list[Container | Volume | Image | Network]]
            Dictionary containing the following keys and corresponding Docker objects.

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
        Unlike the `resources()` method, this method does not group resources by cluster
        or take additional labels to filter by. Fetch containers, volumes, images, and
        networks that are tagged with the global label `ROOT_LABEL`
        (`org.minitrino=root`).
        """
        filter = {"label": [ROOT_LABEL]}
        retval: dict[str, list[Container | Volume | Image | Network]] = {
            "containers": [],
            "volumes": [],
            "images": [],
            "networks": [],
        }

        retval["containers"] = list(
            self._ctx.docker_client.containers.list(filters=filter, all=True)
        )
        retval["volumes"] = list(self._ctx.docker_client.volumes.list(filters=filter))
        retval["images"] = list(
            self._ctx.docker_client.images.list(filters=filter, all=True)
        )
        retval["networks"] = list(self._ctx.docker_client.networks.list(filters=filter))

        return retval

    def compose_project_name(self, cluster_name: str = "") -> str:
        """
        Compute the Docker Compose project name for a cluster.

        Parameters
        ----------
        cluster_name : str, optional
            A specific cluster name. If omitted, uses the current cluster name.

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
        # If we receive a container name with a literal suffix `-${CLUSTER_NAME}`,
        # remove it. In this case, the container name was sourced by reading the Docker
        # Compose file directly, which literally appends `-${CLUSTER_NAME}` to each
        # container name.
        if "-${CLUSTER_NAME}" in name:
            name = name.replace("-${CLUSTER_NAME}", "")
        return f"{name}-{self._ctx.cluster_name}"

    def container(self, fq_container_name: str = "") -> Container:
        """
        Retrieve a Docker container object by fully-qualified name.

        Parameters
        ----------
        fq_container_name : str
            Fully-qualified container name to fetch.

        Returns
        -------
        docker.models.containers.Container
            The matching container object.
        """
        return self._ctx.docker_client.containers.get(fq_container_name)

    def _list_clusters(
        self, resources: dict[str, list[Container | Volume | Image | Network]]
    ) -> list[str]:
        """
        Derive cluster names from Docker resources.

        Parameters
        ----------
        resources : dict[str, list[Container | Volume | Image | Network]]
            Dictionary containing lists of Docker objects keyed by type.

        Returns
        -------
        list[str]
            A sorted list of unique cluster names inferred from Docker resource labels.

        Notes
        -----
        Cluster names cannot be derived from images since they do not maintain a
        one-to-one relationship with a specific cluster.
        """
        cluster_names = []
        for obj_type, objects in resources.items():
            if obj_type == "images":
                continue
            for obj in objects:
                labels = self._docker_labels(obj)
                project = labels.get(COMPOSE_LABEL_KEY) if labels else None
                if project:
                    cluster_names.append(project.split("minitrino-")[1])

        cluster_names = sorted(list(set(cluster_names)))
        self._ctx.logger.verbose(
            f"Identified the following clusters with existing Docker resources: {cluster_names}"
        )
        return cluster_names

    def _filter_by_cluster(
        self,
        resources: dict[str, list[Container | Volume | Image | Network]],
        clusters: list[str],
        addl_labels: Optional[list[str]] = None,
    ) -> dict[str, list[Container | Volume | Image | Network]]:
        """
        Filter Docker resources by cluster name and label criteria.

        Parameters
        ----------
        resources : dict[str, list[Container | Volume | Image | Network]]
            Dictionary of Docker resources categorized by type.
        clusters : list[str]
            List of cluster names used to construct label filters.
        addl_labels : list[str], optional
            Additional label filters to apply to the resources.

        Returns
        -------
        dict[str, list[Container | Volume | Image | Network]]
            Dictionary of filtered Docker resources, organized by type, as native Docker
            objects.

        Notes
        -----
        Resources are grouped by type and filtered using both the required `ROOT_LABEL`
        and the appropriate `COMPOSE_LABEL_KEY` corresponding to each cluster. Images
        are excluded from filtering beyond the standard `ROOT_LABEL` and are returned
        as-is.
        """
        base_labels = list(addl_labels) if addl_labels is not None else []
        if ROOT_LABEL not in base_labels:
            base_labels.append(ROOT_LABEL)

        filtered: dict[str, list] = {k: [] for k in resources.keys()}
        for cluster in clusters:
            docker_labels = list(base_labels)
            docker_labels.append(
                f"{COMPOSE_LABEL_KEY}={self.compose_project_name(cluster)}"
            )
            for obj_type, objects in resources.items():
                for obj in objects:
                    if obj_type == "images":
                        filtered[obj_type].append(obj)
                        continue
                    labels = self._docker_labels(obj)
                    if not labels:
                        continue
                    match = True
                    for label in docker_labels:
                        if "=" not in label:
                            continue
                        k, v = label.split("=")
                        if k not in labels or labels[k] != v:
                            match = False
                            break
                    if match:
                        filtered[obj_type].append(obj)
        for key in filtered:
            seen_ids = set()
            deduped = []
            for obj in filtered[key]:
                if key == "images":
                    image_id = getattr(obj, "id", "")
                    image_tags = getattr(obj, "tags", []) or []
                    obj_id = f"{image_id}|{','.join(image_tags)}"
                else:
                    obj_id = getattr(obj, "id", "")
                if obj_id and obj_id not in seen_ids:
                    seen_ids.add(obj_id)
                    deduped.append(obj)
            filtered[key] = deduped
        return filtered

    def _docker_labels(
        self, obj: Container | Volume | Network | Image
    ) -> dict[str, str]:
        """
        Retrieve Docker labels from a container, volume, network, or image.

        Parameters
        ----------
        obj : Container | Volume | Network | Image
            A Docker object with labels accessible via `.labels` or `.attrs["Labels"]`.

        Returns
        -------
        dict[str, str]
            A dictionary of labels, or an empty dictionary if none are found.
        """
        try:
            labels = getattr(obj, "labels", None)
            if labels:
                return labels
            return obj.attrs.get("Labels", {}) if hasattr(obj, "attrs") else {}
        except Exception:
            return {}


class ClusterResourcesView:
    """
    Provide structured access to Docker resources grouped by cluster.

    Parameters
    ----------
    resources : dict[str, dict[str, list[Container | Volume | Network | Image]]]
        A dictionary of Docker resources grouped by cluster name and object type.

    Notes
    -----
    This class is returned by the `resources()` method and exposes convenient accessors
    for retrieving all containers, volumes, networks, or images across clusters. The
    original grouped dictionary is also accessible via `raw()`.
    """

    def __init__(
        self,
        resources: dict[str, dict[str, list[Container | Volume | Network | Image]]],
    ):
        self._resources = resources

    def containers(self) -> list[ClusterDockerObject]:
        """
        Retrieve all container objects across clusters specified in the context.

        Returns
        -------
        list[ClusterDockerObject]
            A list of all container objects present in the environment.
        """
        return cast(list[ClusterDockerObject], self._collect("containers"))

    def volumes(self) -> list[ClusterDockerObject]:
        """
        Retrieve all volume objects across clusters specified in the context.

        Returns
        -------
        list[ClusterDockerObject]
            A list of all volume objects present in the environment.
        """
        return cast(list[ClusterDockerObject], self._collect("volumes"))

    def networks(self) -> list[ClusterDockerObject]:
        """
        Retrieve all network objects across clusters specified in the context.

        Returns
        -------
        list[ClusterDockerObject]
            A list of all network objects present in the environment.
        """
        return cast(list[ClusterDockerObject], self._collect("networks"))

    def images(self) -> list[Image]:
        """
        Retrieve all global image objects associated with Minitrino.

        These images are not associated with any specific cluster and are grouped
        separately.

        Returns
        -------
        list[Image]
            A list of Docker image objects tagged with the Minitrino project label.
        """
        return cast(list[Image], self._resources.get("images", {}).get("images", []))

    def raw(self) -> dict[str, dict[str, list[Container | Volume | Network | Image]]]:
        """
        Return the full grouped dictionary of Docker resources.

        Returns
        -------
        dict[str, dict[str, list[Container | Volume | Network | Image]]]
            The original dictionary of resources grouped by cluster.

        Examples
        --------
        >>> {
            "default": {
                "containers": [Container("foo"), ...],
                "volumes": [Volume("bar"), ...],
                "networks": [Network("qux"), ...],
            },
            "cluster-1": {
                "containers": [Container("foo"), ...],
                "volumes": [Volume("bar"), ...],
                "networks": [Network("qux"), ...],
            },
            "images": {
                "images": [Image("baz"), ...]
            }
        }
        """
        return self._resources

    def _collect(self, key: str) -> list[ClusterDockerObject]:
        """
        Collect Docker resources (containers, volumes, networks) across all clusters.

        Parameters
        ----------
        key : str
            The resource type to collect (containers, volumes, or networks).

        Returns
        -------
        list[ClusterDockerObject]
            A flat list of resource objects wrapped with their associated cluster
            metadata.
        """
        result = []
        for cluster, resources in self._resources.items():
            if cluster == "images":
                continue
            for obj in resources.get(key, []):
                result.append(ClusterDockerObject(obj, cluster))
        return result


class ClusterDockerObject:
    """
    Wrap a Docker object that can be associated with a cluster.

    Parameters
    ----------
    obj : Container | Volume | Network
        The Docker object to wrap.
    cluster : str
        The name of the associated cluster.
    """

    def __init__(self, obj: Container | Volume | Network, cluster: str):
        self.obj = obj
        self.cluster = cluster

    def __getattr__(self, name: str) -> Container | Volume | Network:
        """Delegate attribute access to the wrapped Docker object.

        Parameters
        ----------
        name : str
            The attribute name to access.

        Returns
        -------
        Container | Volume | Network
            The attribute value from the wrapped Docker object.
        """
        return getattr(self.obj, name)
