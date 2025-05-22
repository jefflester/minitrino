"""Cluster operations and resource management for Minitrino clusters."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Optional

from docker.errors import APIError, NotFound

from minitrino import utils
from minitrino.core.docker.wrappers import (
    MinitrinoContainer,
    MinitrinoDockerObject,
    MinitrinoImage,
    MinitrinoNetwork,
)
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.logger import LogLevel
from minitrino.settings import (
    CLUSTER_CONFIG,
    ETC_DIR,
    WORKER_CONFIG_PROPS,
)

if TYPE_CHECKING:
    from minitrino.core.cluster.cluster import Cluster
    from minitrino.core.context import MinitrinoContext


class ClusterOperations:
    """
    Cluster operations manager for the current cluster.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and
        context.
    cluster : Cluster
        An instantiated `Cluster` object.

    Methods
    -------
    down(sig_kill: bool = False, keep: bool = False)
        Stops and optionally removes all containers for the current
        cluster.
    remove(obj_type: str, force: bool, labels: Optional[list[str]] =
    None)
        Removes Docker objects (images, volumes, or networks) associated
        with the current cluster.
    restart()
        Restarts all cluster containers (coordinator and workers).
    restart_containers(c_restart: Optional[list[str]] = None, log_level:
    LogLevel = LogLevel.DEBUG)
        Restarts all the containers in the provided list. Can apply to
        any container in the environment, not just the coordinator and
        workers.
    rollback()
        Terminates the provision operations and removes the cluster.
    provision_workers(workers: int)
        Provisions or adjusts worker containers based on the specified
        number.
    """

    def __init__(self, ctx: MinitrinoContext, cluster: Cluster):
        self._ctx = ctx
        self._cluster = cluster

    def down(self, sig_kill: bool = False, keep: bool = False) -> None:
        """
        Stop and optionally remove all containers from the cluster.

        Parameters
        ----------
        sig_kill : bool, optional
            If True, containers will be stopped using SIGKILL instead of
            SIGTERM.
        keep : bool, optional
            If True, containers will be stopped but not removed.
        """
        resources = self._cluster.resource.resources()
        containers = resources.containers()

        if len(containers) == 0:
            self._ctx.logger.info("No containers to bring down.")
            return

        def stop_container(container: MinitrinoContainer):
            identifier = utils.generate_identifier(
                {"ID": container.short_id, "Name": container.name}
            )
            if container.status == "running":
                if sig_kill:
                    container.kill()
                else:
                    container.stop()
                self._ctx.logger.info(f"Stopped container: {identifier}")
            return container

        def remove_container(container: MinitrinoContainer):
            identifier = utils.generate_identifier(
                {"ID": container.short_id, "Name": container.name}
            )
            container.remove()
            self._ctx.logger.info(f"Removed container: {identifier}")

        with ThreadPoolExecutor() as executor:
            stop_futures = {
                executor.submit(stop_container, container): container
                for container in containers
            }
            for future in as_completed(stop_futures):
                container = stop_futures[future]
                try:
                    future.result()
                except Exception as e:
                    self._ctx.logger.error(
                        f"Error stopping container '{container.name}': {str(e)}"
                    )

        if not keep:
            with ThreadPoolExecutor() as executor:
                remove_futures = {
                    executor.submit(remove_container, container): container
                    for container in containers
                }
                for future in as_completed(remove_futures):
                    container = remove_futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        self._ctx.logger.error(
                            f"Error removing container '{container.name}': {str(e)}"
                        )

        self._ctx.logger.info("Brought down all Minitrino containers.")

    def remove(
        self, obj_type: str, force: bool, modules: Optional[list[str]] = None
    ) -> None:
        """
        Remove Docker objects associated with the current cluster.

        Parameters
        ----------
        obj_type : str
            Type of Docker object to remove. Must be an image, volume,
            or network.
        force : bool
            If True, forces removal even if the resource is in use.
        modules : list[str], optional
            Module names to filter which resources should be removed.

        Raises
        ------
        UserError
            If attempting to remove images for a specific cluster or
            module.

        Notes
        -----
        This method deletes the specified Docker resource type(s)
        filtered by labels (sourced from provided modules, cluster name,
        or the project root label).

        Because images are global project resources (they are not tied
        to any one cluster or module), they can only be removed as a
        global operation (using `--cluster all` and omitting
        `--module`).
        """
        modules = modules or []
        if obj_type == "image":
            if modules:
                self._ctx.logger.warn(
                    "Cannot remove images for a specific module. "
                    "Skipping image removal."
                )
                return
            if not self._ctx.all_clusters:
                self._ctx.logger.warn(
                    "Cannot remove images for a specific cluster. "
                    "Skipping image removal."
                )
                return

        labels = []
        for module_name in modules:
            module: dict | None = self._ctx.modules.data.get(module_name)
            if module is None:
                raise UserError(f"Module '{module_name}' not found.")
            labels.append(module["label"])

        resources = self._cluster.resource.resources(labels)
        items: list[MinitrinoDockerObject]
        if obj_type == "image":
            items = list(resources.images())
        elif obj_type == "volume":
            items = list(resources.volumes())
        elif obj_type == "network":
            items = list(resources.networks())
        else:
            raise ValueError(f"Invalid object type: {obj_type}")

        for obj in items:
            identifier = "<unknown>"
            try:
                fields = self._get_identifier_fields(obj_type, obj)
                identifier = utils.generate_identifier(fields)
                if obj.kind == "network":
                    obj.remove()
                else:
                    assert not isinstance(obj, MinitrinoNetwork)
                    obj.remove(force=force)
                self._ctx.logger.info(f"{obj_type.title()} removed: {identifier}")
            except APIError as e:
                self._ctx.logger.debug(
                    f"Cannot remove {obj_type}: {identifier}\n"
                    f"Error from Docker: {e.explanation}"
                )

    def restart(self) -> None:
        """Restart all cluster containers (coordinator and workers)."""
        cluster_resources = self._cluster.resource.resources()
        containers = cluster_resources.containers()

        if len(containers) == 0:
            self._ctx.logger.info("No cluster containers to restart.")
            return

        cluster_containers = [c.name for c in containers if c.name]

        self.restart_containers(cluster_containers, log_level=LogLevel.INFO)
        self._ctx.logger.info(
            f"Restarted containers in cluster '{self._ctx.cluster_name}'."
        )

    def restart_containers(
        self,
        c_restart: Optional[list[str]] = None,
        log_level: LogLevel = LogLevel.DEBUG,
    ) -> None:
        """
        Restart all the containers in the provided list.

        Parameters
        ----------
        c_restart : Optional[list[str]], optional
            List of fully-qualified container names to restart, by
            default None.
        log_level : LogLevel, optional
            Log level for restart messages, by default LogLevel.DEBUG.
        """
        if c_restart is None:
            return

        c_restart = list(set(c_restart))

        def _restart_container(container_name: str) -> None:
            """
            Restart a single container by name.

            Parameters
            ----------
            container_name : str
                The name of the container to restart.

            Raises
            ------
            MinitrinoError
                If the container is not found.
            """
            try:
                container = self._ctx.docker_client.containers.get(container_name)
                self._ctx.logger.log(
                    f"Restarting container '{container.name}'...", level=log_level
                )
                container.restart()
                self._ctx.logger.log(
                    f"Container '{container.name}' restarted successfully.",
                    level=log_level,
                )
            except NotFound:
                raise MinitrinoError(
                    f"Attempting to restart container '{container_name}', "
                    f"but the container was not found."
                )

        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(_restart_container, container): container
                for container in c_restart
            }

            for future in as_completed(futures):
                container_name = futures[future]
                try:
                    future.result()
                except MinitrinoError as e:
                    self._ctx.logger.error(
                        f"Error while restarting container '{container_name}': {str(e)}"
                    )

    def rollback(self) -> None:
        """Terminate the provision operations and remove the cluster."""
        self._ctx.logger.warn(
            f"Rolling back cluster '{self._ctx.cluster_name}'...",
        )
        resources = self._cluster.resource.resources()
        containers = resources.containers()
        for c in containers:
            try:
                c.kill()
                self._ctx.logger.debug(f"Rolled back {repr(c)}")
            except Exception:
                pass
            try:
                c.remove()
                self._ctx.logger.debug(f"Rolled back {repr(c)}")
            except Exception:
                pass

    def provision_workers(self, workers: int = 0) -> None:
        """Reconcile number of workers with the specified number."""
        # Handles five scenarios:
        #  1. No `workers` value is provided and no workers are
        #     currently running — does nothing.
        #  2. A positive `workers` value is provided and no workers
        #     exist — provisions new workers.
        #  3. No `workers` value is provided but some are already
        #     running — uses current count.
        #  4. Provided `workers` value is greater than running workers —
        #     provisions more workers.
        #  5. Provided `workers` value is less than running workers —
        #     removes excess workers.

        pattern = rf"minitrino-worker-\d+-{self._ctx.cluster_name}"
        worker_containers = [
            c.name
            for c in self._cluster.resource.resources().containers()
            if c.name
            and re.match(pattern, c.name)
            and c.name.startswith("minitrino-worker-")
            and c.labels.get("org.minitrino") == "root"
        ]
        running_workers = len(worker_containers)

        # Scenario 1
        if workers == 0 and running_workers == 0:
            return

        # Scenario 3
        if workers == 0 and running_workers > 0:
            workers = running_workers

        # Scenario 4
        if workers > running_workers:
            self._ctx.logger.info(f"Adding {workers} workers...")

        # Scenario 5
        if workers < running_workers:
            worker_containers.sort(reverse=True)
            excess = running_workers - workers
            remove = [name for name in worker_containers[:excess] if name]
            for name in remove:
                container_obj = self._cluster.resource.container(name)
                container_obj.kill()
                container_obj.remove()
                identifier = utils.generate_identifier(
                    {"ID": container_obj.short_id, "Name": container_obj.name}
                )
                self._ctx.logger.warn(f"Removed excess worker: {identifier}")

        ver = self._ctx.env.get("CLUSTER_VER")
        dist = self._ctx.env.get("CLUSTER_DIST")
        worker_img = f"minitrino/cluster:{ver}-{dist}"

        compose_project_name = self._cluster.resource.compose_project_name()
        network_name = f"minitrino_{self._ctx.cluster_name}"
        fq_container_name = self._cluster.resource.fq_container_name("minitrino")
        coordinator = self._cluster.resource.container(fq_container_name)

        restart = []
        for i in range(1, workers + 1):
            fq_worker_name = self._cluster.resource.fq_container_name(
                f"minitrino-worker-{i}",
            )
            try:
                worker = self._cluster.resource.container(fq_worker_name)
            except NotFound:
                worker_base = self._ctx.docker_client.containers.run(
                    worker_img,
                    name=fq_worker_name,
                    detach=True,
                    network=network_name,
                    labels={
                        "org.minitrino": "root",
                        "org.minitrino.module": "minitrino",
                        "com.docker.compose.project": compose_project_name,
                        "com.docker.compose.service": "minitrino-worker",
                    },
                )
                worker = MinitrinoContainer(worker_base, self._ctx.cluster_name)
                self._ctx.logger.debug(
                    f"Created and started worker container: '{fq_worker_name}' "
                    f"in network '{network_name}'"
                )

            user = self._ctx.env.get("BUILD_USER")
            tar_path = "/tmp/${CLUSTER_DIST}.tar.gz"

            # Copy the source directory from the coordinator to the
            # worker container
            self._ctx.cmd_executor.execute(
                f"bash -c 'tar czf {tar_path} -C /etc ${{CLUSTER_DIST}}'",
                container=coordinator,
                docker_user=user,
            )

            # Copy the tar file from the coordinator container
            bits, _ = coordinator.get_archive(
                f"/tmp/{self._ctx.env.get('CLUSTER_DIST')}.tar.gz"
            )
            tar_stream = b"".join(bits)

            worker.put_archive("/tmp", tar_stream)

            # Put the tar file into the new worker container & extract
            self._ctx.cmd_executor.execute(
                f"bash -c 'tar xzf {tar_path} -C /etc'",
                container=worker,
                docker_user=user,
            )

            # Overwrite worker config.properties
            self._ctx.cmd_executor.execute(
                f"bash -c \"echo '{WORKER_CONFIG_PROPS}' "
                f'> {ETC_DIR}/{CLUSTER_CONFIG}"',
                container=worker,
                docker_user=user,
            )

            restart.append(fq_worker_name)
            self._ctx.logger.debug(f"Copied {ETC_DIR} to '{fq_worker_name}'")

        self.restart_containers(restart)

    def _get_identifier_fields(
        self, obj_type: str, item: MinitrinoDockerObject
    ) -> dict[str, str]:
        """
        Return a dictionary of identifying fields for Docker resources.

        Parameters
        ----------
        obj_type : str
            Type of Docker object (container, image, volume, network).
        item : docker.models object
            The Docker object to extract metadata from.

        Returns
        -------
        dict[str, str]
            Mapping of human-readable keys and values.
        """
        if obj_type == "image":
            id_val = item.short_id
            tag_val = "<none>"
            # Narrow item to MinitrinoImage before calling
            # _try_get_image_tag
            if isinstance(item, MinitrinoImage):
                tag_val = self._try_get_image_tag(item)
                tag_val = "<none>" if not tag_val else tag_val
            return {"ID": id_val, "Image:Tag": tag_val}
        else:
            id_val = (
                getattr(item, "name", None)
                or f"<unnamed-{item.kind}-{item.cluster_name}>"
            )
            return {"ID": id_val}

    def _try_get_image_tag(self, image: MinitrinoImage) -> str:
        """Safely fetch the first tag from an image."""
        try:
            return image.tags[0]
        except Exception:
            return ""
