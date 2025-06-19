"""Cluster operations and resource management for Minitrino clusters."""

from __future__ import annotations

import re
import time
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

        module_labels = []
        for module_name in modules:
            module: dict | None = self._ctx.modules.data.get(module_name)
            if module is None:
                raise UserError(f"Module '{module_name}' not found.")
            module_labels.append(module["label"])
        if not module_labels:
            self._remove(obj_type, None, force)
            return
        for label in module_labels:
            self._remove(obj_type, label, force)

    def restart(self) -> None:
        """Restart all cluster containers (coordinator and workers)."""
        cluster_resources = self._cluster.resource.resources()
        containers = cluster_resources.containers()

        if len(containers) == 0:
            self._ctx.logger.info("No cluster containers to restart.")
            return

        cluster_containers = [c.name for c in containers if c.name]
        self.restart_containers(cluster_containers)
        self._ctx.logger.info(
            f"Restarted containers in cluster '{self._ctx.cluster_name}'."
        )

    def restart_containers(self, c_restart: Optional[list[str]] = None) -> None:
        """
        Restart all the containers in the provided list.

        Parameters
        ----------
        c_restart : Optional[list[str]], optional
            List of fully-qualified container names to restart, by
            default None.
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
                self._ctx.logger.debug(f"Restarting container '{container.name}'...")
                container.restart()
                self._ctx.logger.debug(
                    f"Container '{container.name}' restarted successfully."
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
        """Provision the specified number of workers."""
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

        self._wait_for_config_copy_log()

        pattern = rf"minitrino-worker-\d+-{self._ctx.cluster_name}"
        worker_containers = [
            c.name
            for c in self._cluster.resource.resources().containers()
            if c.name
            and re.match(pattern, c.name)
            and c.name.startswith("minitrino-worker-")
            and c.labels.get("org.minitrino.root") == "true"
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
                env_list = coordinator.attrs["Config"]["Env"]
                env_dict = dict(item.split("=", 1) for item in env_list if "=" in item)
                worker_base = self._ctx.docker_client.containers.run(
                    worker_img,
                    name=fq_worker_name,
                    environment=env_dict,
                    detach=True,
                    network=network_name,
                    labels={
                        "org.minitrino.root": "true",
                        "org.minitrino.module.minitrino": "true",
                        "com.docker.compose.project": compose_project_name,
                        "com.docker.compose.service": "minitrino-worker",
                    },
                )
                shared_network = self._ctx.docker_client.networks.get("cluster_shared")
                shared_network.connect(worker_base)

                worker = MinitrinoContainer(worker_base, self._ctx.cluster_name)
                self._ctx.logger.debug(
                    f"Created and started worker container: '{fq_worker_name}' "
                    f"in network '{network_name}'."
                )

            user = self._ctx.env.get("SERVICE_USER")
            tar_path = "/tmp/${CLUSTER_DIST}.tar.gz"

            # Create tar archive of coordinator's /etc/${CLUSTER_DIST}
            self._ctx.cmd_executor.execute(
                "bash -c 'rm -rf /tmp/${CLUSTER_DIST}_copy'",
                "bash -c 'cp -a /etc/${CLUSTER_DIST} /tmp/${CLUSTER_DIST}_copy'",
                f"bash -c 'tar czf {tar_path} -C /tmp/${{CLUSTER_DIST}}_copy .'",
                "bash -c 'rm -rf /tmp/${CLUSTER_DIST}_copy'",
                container=coordinator,
                docker_user=user,
            )

            # Copy the tar archive from the coordinator container
            bits, _ = coordinator.get_archive(
                f"/tmp/{self._ctx.env.get('CLUSTER_DIST')}.tar.gz"
            )
            tar_stream = b"".join(bits)

            worker.put_archive("/tmp", tar_stream)

            # Extract the tar archive into the new worker container
            self._ctx.cmd_executor.execute(
                f"bash -c 'tar xzf {tar_path} -C /etc/${{CLUSTER_DIST}}'",
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

    def _wait_for_config_copy_log(self, timeout: int = 30) -> None:
        """Poll the coordinator container logs for finished message."""
        fq_container_name = self._cluster.resource.fq_container_name("minitrino")
        coordinator = self._cluster.resource.container(fq_container_name)
        start = time.time()
        found = False
        while time.time() - start < timeout:
            logs = coordinator.logs(tail=500).decode("utf-8", errors="replace")
            if "Finished copying configs" in logs:
                found = True
                break
            time.sleep(1)
        if not found:
            raise TimeoutError(
                "Timed out waiting for 'Finished copying configs' in coordinator logs."
            )

    def _remove(self, obj_type: str, label: str | None, force: bool) -> None:
        resources = self._cluster.resource.resources([label] if label else None)
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
                    assert isinstance(obj, MinitrinoNetwork)
                    obj.remove()
                else:
                    assert not isinstance(obj, MinitrinoNetwork)
                    obj.remove(force=force)
                self._ctx.logger.info(f"{obj_type.title()} removed: {identifier}")
            except APIError as e:
                self._ctx.logger.info(
                    f"Cannot remove {obj_type}: {identifier}\n"
                    f"Error from Docker: {e.explanation}"
                )

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
