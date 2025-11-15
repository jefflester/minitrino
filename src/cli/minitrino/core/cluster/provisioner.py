"""Cluster operations and resource management for Minitrino clusters."""

from __future__ import annotations

import hashlib
import os
import shutil
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from docker.errors import NotFound

from minitrino import utils
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.shutdown import shutdown_event

if TYPE_CHECKING:
    from minitrino.core.cluster.cluster import Cluster
    from minitrino.core.context import MinitrinoContext


class ClusterProvisioner:
    """Provision the cluster and provided modules.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and
        context.
    cluster : Cluster
        An instantiated `Cluster` object.

    Methods
    -------
    provision()
        Provision the cluster and provided modules.
    """

    def __init__(self, ctx: MinitrinoContext, cluster: Cluster):
        self._ctx = ctx
        self._cluster = cluster

        self.modules: list[str] = []
        self.image: str = "trino"
        self.workers: int = 0
        self.no_rollback: bool = False
        self.build: bool = False
        self._captured_container_logs: str = ""  # Store container logs before rollback

        self._worker_safe_event: threading.Event = threading.Event()
        self._dep_cluster_env: dict[str, str] = {}

    def provision(
        self,
        modules: list[str],
        image: str,
        workers: int,
        no_rollback: bool,
    ) -> None:
        """Provision the cluster and provided modules.

        Notes
        -----
        - Should always be invoked from `ClusterOperations.provision()`.
        - Writes a crashdump log to the user directory if an exception
          is raised.
        """

        def _orchestrate():
            if self._ctx.all_clusters:
                raise UserError(
                    "The `provision` command cannot interact with multiple/all"
                    " clusters. Please specify a valid cluster name containing only"
                    " alphanumeric, hyphen, and underscore characters."
                )

            self.modules = modules
            self.image = image
            self.workers = workers
            self.no_rollback = no_rollback
            self._set_license()
            self._set_distribution()
            self.build = self._determine_build()

            for module in self.modules:
                self._ctx.modules.validate_module_name(module)
            if not self.modules:
                self._ctx.logger.info(
                    f"No modules specified. Provisioning standalone "
                    f"{self._ctx.env.get('CLUSTER_DIST').title()} cluster..."
                )

            utils.check_daemon(self._ctx.docker_client)
            utils.check_lib(self._ctx)
            self._ctx.cluster.validator.check_cluster_ver()
            self._ctx.modules.check_module_version_requirements(self.modules)
            self.modules = self._append_running_modules(self.modules)
            self.modules = self._ctx.modules.check_dep_modules(self.modules)

            dependent_clusters = self._ctx.cluster.validator.check_dependent_clusters(
                self.modules
            )

            clusters_to_provision = [None]  # None represents main cluster
            clusters_to_provision.extend(dependent_clusters)

            try:
                self._ensure_shared_network()
                self._runner()  # Provisions main cluster
                for cluster in dependent_clusters:
                    self._runner(cluster=cluster)
                self._record_image_src_checksum()
                self._ctx.logger.info("Environment provisioning complete.")
            except Exception as e:
                self._ctx.logger.error(
                    "Provisioning failed. Rolling back all provisioned clusters..."
                )
                # Capture container logs before rollback destroys them
                self._capture_container_logs_for_crashdump()
                self._rollback()
                raise e

        try:
            _orchestrate()
        except UserError as e:
            raise e
        except Exception as e:
            crashdump = os.path.join(self._ctx.minitrino_user_dir, "crashdump.log")
            self._ctx.logger.error(
                f"{str(e)}\nFull provision log written to {crashdump}"
            )
            with open(crashdump, "w") as f:
                # Write Minitrino logs
                f.write("=" * 80 + "\n")
                f.write("MINITRINO LOGS\n")
                f.write("=" * 80 + "\n\n")
                for msg, _, is_spinner in self._ctx.logger._log_sink.buffer:
                    if not is_spinner:
                        f.write(msg + "\n")

                # Write captured container logs
                f.write("\n\n")
                if self._captured_container_logs:
                    f.write(self._captured_container_logs)
                else:
                    f.write("=" * 80 + "\n")
                    f.write("CONTAINER LOGS\n")
                    f.write("=" * 80 + "\n\n")
                    f.write("No container logs were captured.\n")
            raise MinitrinoError(
                f"{str(e)}\nFull provision log written to {crashdump}"
            ) from e

    def _runner(self, cluster: dict | None = None) -> None:
        """Execute the provisioning sequence for a cluster and modules.

        If provisioning a dependent cluster, update the cluster context,
        instance attributes, and environment variables before executing
        the provisioning sequence.

        Parameters
        ----------
        cluster : dict, optional
            Optional dictionary representing a dependent cluster
            configuration. Defaults to None.
        """
        if cluster is None:
            cluster = {}

        self._worker_safe_event.clear()

        log_dist = self._ctx.env.get("CLUSTER_DIST")
        self._ctx.logger.info(f"Starting {log_dist.title()} cluster provisioning...")

        # If a dependent cluster is being provisioned, we need to update
        # the context to the dependent cluster's values, then update the
        # environment variables so that the Compose YAMLs use the
        # correct values.
        if cluster:
            self._ctx.logger.info(
                f"Provisioning dependent cluster: {cluster['name']}..."
            )
            self.modules = self._ctx.modules.check_dep_modules(
                cluster.get("modules", [])
            )
            self.workers = cluster.get("workers", 0)
            self._ctx.cluster_name = cluster.get("name", "")
            if cluster and cluster.get("env"):
                self._dep_cluster_env.clear()
                self._ctx.logger.debug(
                    f"Loading dependent cluster env vars: {cluster['env']}"
                )
                self._dep_cluster_env.update(cluster.get("env", {}))

        self._set_env_vars()
        self._ctx.provisioned_clusters.append(self._ctx.cluster_name)

        self._ctx.modules.check_enterprise(self.modules)
        self._ctx.modules.check_compatibility(self.modules)
        self._ctx.modules.check_volumes()
        self._ctx.cluster.ports.set_external_ports(self.modules)

        try:
            module_yaml_paths = self._module_yaml_paths()
            compose_cmd = self._build_compose_command(module_yaml_paths)

            worker_thread = None
            if self.workers > 0:
                worker_thread = threading.Thread(
                    target=self._provision_workers_when_safe,
                    name="ProvisionWorkersThread",
                    daemon=True,
                )
                worker_thread.start()

            self._run_compose_and_wait(compose_cmd)

            if worker_thread:
                worker_thread.join()

            self._ctx.cluster.validator.check_dup_config()

        except Exception as e:
            self._rollback()
            raise MinitrinoError("Failed to provision cluster.") from e

    def _capture_container_logs_for_crashdump(self) -> None:
        """Capture container logs before rollback destroys them.

        Stores logs in self._captured_container_logs for later use in crashdump.
        """
        logs_buffer = []
        logs_buffer.append("=" * 80 + "\n")
        logs_buffer.append("CONTAINER LOGS\n")
        logs_buffer.append("=" * 80 + "\n\n")

        # Save current cluster name to restore later
        original_cluster_name = self._ctx.cluster_name
        total_containers = 0

        # Debug: Log provisioned clusters
        self._ctx.logger.debug(
            f"Capturing logs for provisioned clusters: {self._ctx.provisioned_clusters}"
        )
        logs_buffer.append(
            f"Provisioned clusters: {self._ctx.provisioned_clusters}\n\n"
        )

        try:
            # Iterate through all provisioned clusters
            for cluster_name in self._ctx.provisioned_clusters:
                self._ctx.cluster_name = cluster_name  # Activate cluster in context
                logs_buffer.append(f"\n{'=' * 80}\n")
                logs_buffer.append(f"Cluster: {cluster_name}\n")
                logs_buffer.append(f"{'=' * 80}\n\n")

                try:
                    # Get all containers for this cluster
                    resources = self._ctx.cluster.resource.resources()
                    containers = list(resources.containers())

                    if containers:
                        total_containers += len(containers)
                        for container in containers:
                            logs_buffer.append(
                                f"\n--- Container: {container.name} ---\n"
                            )
                            logs_buffer.append(f"Status: {container.status}\n")
                            logs_buffer.append(f"ID: {container.id[:12]}\n")
                            try:
                                logs = container.logs().decode(
                                    "utf-8", errors="replace"
                                )
                                logs_buffer.append(f"\nLogs:\n{logs}\n")
                            except Exception as log_err:
                                logs_buffer.append(
                                    f"\nFailed to retrieve logs: {log_err}\n"
                                )
                            logs_buffer.append("-" * 80 + "\n")
                    else:
                        logs_buffer.append("No containers found for this cluster.\n")
                except Exception as cluster_err:
                    logs_buffer.append(
                        f"\nFailed to retrieve containers for cluster "
                        f"'{cluster_name}': {cluster_err}\n"
                    )

            if total_containers == 0:
                logs_buffer.append(
                    "\nNo containers found across all provisioned clusters.\n"
                )

        except Exception as container_err:
            logs_buffer.append(
                f"\nFailed to retrieve container information: {container_err}\n"
            )
        finally:
            # Restore original cluster name
            self._ctx.cluster_name = original_cluster_name

        self._captured_container_logs = "".join(logs_buffer)

    def _provision_workers_when_safe(self) -> None:
        """Wait for the worker-safe event, then provision workers.

        Notes
        -----
        This method is intended to be run in a background thread. It
        waits until the coordinator container signals that workers can
        be safely provisioned, then provisions the requested number of
        workers.
        """
        self._ctx.logger.debug(
            "Waiting for worker-safe signal before provisioning workers..."
        )
        self._worker_safe_event.wait()
        self._ctx.logger.debug(
            "Worker-safe signal received. Proceeding to provision workers."
        )
        with self._ctx.logger.spinner(f"Provisioning {self.workers} workers..."):
            self._ctx.cluster.ops.reconcile_workers(self.workers)
            self._ctx.logger.info(f"{self.workers} workers provisioned successfully.")

    def _set_distribution(self) -> None:
        """Determine the cluster distribution.

        Set the distribution for the cluster based on the configuration.
        """
        if not self.image:
            self.image = self._ctx.env.get("IMAGE", "trino")
        if self.image != "trino" and self.image != "starburst":
            raise UserError(
                f"Invalid image type '{self.image}'. Please specify either 'trino' "
                "or 'starburst'.",
                "Example: `minitrino provision -i trino`. This can also be set "
                "permanently via `minitrino config`.",
            )

        self._ctx.env.update({"CLUSTER_DIST": self.image})
        self._ctx.env.update({"SERVICE_USER": self.image})
        self._ctx.env.update({"ETC": f"/etc/{self.image}"})

    def _ensure_shared_network(self) -> None:
        """Ensure the shared network exists."""
        try:
            self._ctx.docker_client.networks.get("cluster_shared")
            self._ctx.logger.debug("Shared network already exists, skipping creation.")
        except NotFound:
            self._ctx.logger.debug("Creating shared network...")
            self._ctx.docker_client.networks.create(
                name="cluster_shared",
                driver="bridge",
                labels={
                    "org.minitrino.root": "true",
                    "org.minitrino.module.minitrino": "true",
                    "com.docker.compose.project": "minitrino-system",
                },
            )

    def _append_running_modules(self, modules: list[str] | None = None) -> list[str]:
        """Add running modules to the modules list.

        Parameters
        ----------
        modules : list[str]
            The list of modules to provision.

        Returns
        -------
        list[str]
            The list of modules to provision, including any running
            modules.
        """
        self._ctx.logger.debug("Checking for running modules...")
        running_modules = self._ctx.modules.running_modules()

        if running_modules:
            self._ctx.logger.debug(
                f"Identified the following running modules: "
                f"{list(running_modules.keys())}. Appending "
                "the running module list to the list "
                "of modules to provision.",
            )

        modules = modules if modules is not None else []
        modules.extend(running_modules.keys())
        return list(set(modules))

    def _module_yaml_paths(self) -> list[str]:
        """Return a list of YAML file paths for enabled modules.

        Returns
        -------
        list[str]
            List of Compose YAML file paths for enabled modules.
        """
        root_compose = os.path.join(self._ctx.lib_dir, "docker-compose.yaml")
        paths = [root_compose]
        for module in self.modules:
            yaml_file = self._ctx.modules.data.get(module, {}).get("yaml_file", "")
            paths.append(yaml_file)
        return paths

    def _resolve_compose_bin(self) -> tuple[str, list[str]]:
        """Resolve the Docker Compose executable and base command.

        Returns
        -------
        tuple[str, list[str]]
            Tuple of (compose_bin, base_args). compose_bin is the full
            path to the executable, base_args is the argument list
            (e.g., ['compose']) if using the plugin, or [] if using the
            legacy binary.

        Raises
        ------
        RuntimeError
            If neither docker nor docker-compose is found in PATH.
        """
        docker_bin = shutil.which("docker")
        docker_compose_bin = shutil.which("docker-compose")
        if docker_bin is not None:
            return docker_bin, ["compose"]
        elif docker_compose_bin is not None:
            return docker_compose_bin, []
        else:
            raise MinitrinoError(
                "Neither 'docker' nor 'docker-compose' was found in PATH."
            )

    def _build_compose_command(
        self, module_yaml_paths: list[str] | None = None
    ) -> list[str]:
        """Build the Docker Compose command as a list of arguments.

        Parameters
        ----------
        module_yaml_paths : Optional[list[str]], optional
            List of module YAML file paths to include with -f flags.

        Returns
        -------
        list[str]
            The Docker Compose command as a list of arguments.
        """
        compose_bin, base_args = self._resolve_compose_bin()
        cmd = [compose_bin] + base_args
        if module_yaml_paths:
            for yaml_path in module_yaml_paths:
                cmd += ["-f", yaml_path]
        cmd += ["up", "-d", "--force-recreate"]
        if self.build:
            cmd.append("--build")
        return cmd

    def _module_string(self) -> str:
        """Return a comma-separated string of modules."""
        return ",".join(self.modules)

    def _set_env_vars(self) -> None:
        """Set environment variables for the cluster."""
        self._ctx.env.update({"WORKERS": str(self.workers)})
        self._ctx.env.update({"CLUSTER_NAME": self._ctx.cluster_name})
        self._ctx.env.update({"MINITRINO_MODULES": self._module_string()})
        compose_project_name = self._ctx.cluster.resource.compose_project_name()
        self._ctx.env.update({"COMPOSE_PROJECT_NAME": compose_project_name})

    def _run_compose_and_wait(self, compose_cmd: list[str]) -> None:
        """Run the compose command asynchronously.

        Parameters
        ----------
        compose_cmd : list[str]
            The docker compose command to execute (as a list of
            arguments).
        """
        if "COMPOSE_BAKE" not in self._ctx.env:
            self._ctx.env["COMPOSE_BAKE"] = "true"

        env = self._ctx.env.copy()
        env.update(self._dep_cluster_env)

        # Use the new stream_execute_with_result API for fast failure detection
        output_iterator, completion_event, get_result = (
            self._ctx.cmd_executor.stream_execute_with_result(
                compose_cmd, environment=env, suppress_output=True
            )
        )

        self._compose_failed = threading.Event()
        self._compose_error: BaseException | None = None
        self._compose_output_lines: list[str] = []

        def _run_compose() -> None:
            """Stream compose output and capture errors."""
            try:
                for line in output_iterator:
                    self._ctx.logger.debug(line)
                    self._compose_output_lines.append(line)

                    # Check if the process failed quickly (validation errors, etc.)
                    if completion_event.is_set():
                        result = get_result()
                        if result.exit_code != 0:
                            self._compose_failed.set()
                            self._compose_error = MinitrinoError(
                                f"Docker Compose command failed with exit code "
                                f"{result.exit_code}.\n"
                                f"Command: {' '.join(compose_cmd)}\n"
                                f"Output:\n{''.join(self._compose_output_lines)}"
                            )
                            return
            except Exception as exc:
                self._compose_failed.set()
                self._compose_error = exc

        fq_container_name = self._ctx.cluster.resource.fq_container_name("minitrino")
        try:
            orig_container = self._ctx.cluster.resource.container(fq_container_name)
            orig_container_id = orig_container.id
            self._ctx.logger.debug(
                f"Original coordinator container ID: {orig_container_id}"
            )
        except NotFound:
            orig_container_id = None

        compose_thread = threading.Thread(target=_run_compose)
        compose_thread.start()
        self._ctx.logger.debug("Compose command started asynchronously.")

        spinner_msg = (
            "Building Minitrino image..."
            if self.build
            else "Starting Minitrino environment..."
        )
        with self._ctx.logger.spinner(spinner_msg):
            try:
                self._wait_for_coordinator_container(
                    orig_container_id,
                    compose_thread,
                    completion_event,
                    get_result,
                )
            finally:
                compose_thread.join()

        # Final check after thread completion
        if self._compose_failed.is_set():
            raise MinitrinoError(
                "Docker Compose command failed."
            ) from self._compose_error

        # Check final result if not already failed
        if completion_event.is_set():
            result = get_result()
            if result.exit_code != 0:
                raise MinitrinoError(
                    f"Docker Compose command failed with exit code "
                    f"{result.exit_code}.\n"
                    f"Command: {' '.join(compose_cmd)}\n"
                    f"Output:\n{''.join(self._compose_output_lines)}"
                )

    def _wait_for_coordinator_container(
        self,
        orig_container_id: str | None,
        compose_thread: threading.Thread,
        completion_event: threading.Event,
        get_result: Callable,
        timeout: int = 180,
    ) -> None:
        """Wait for the coordinator container to be running.

        Parameters
        ----------
        orig_container_id : str | None
            ID of the original coordinator container.
        compose_thread : threading.Thread
            Thread running the compose command.
        completion_event : threading.Event
            Event signaling compose command completion.
        get_result : Callable
            Function to get the final command result.
        """
        timeout = (
            int(self._ctx.env.get("PROVISION_BUILD_TIMEOUT", 1200))
            if self.build
            else 120
        )
        # Use longer timeout for builds even after container creation
        default_timeout = 300 if self.build else 120
        reset_timeout = False
        poll_start = time.time()
        while True:
            # Check for early compose failure (e.g., validation errors)
            if completion_event.is_set() and not compose_thread.is_alive():
                result = get_result()
                if result.exit_code != 0:
                    # Docker Compose failed quickly - likely validation error
                    raise MinitrinoError(
                        f"Docker Compose failed with exit code {result.exit_code}.\n"
                        f"This often indicates a configuration or validation error.\n"
                        f"Output:\n{''.join(self._compose_output_lines)}"
                    )

            if self._compose_failed.is_set():
                raise MinitrinoError(
                    "Docker Compose command failed."
                ) from self._compose_error
            if shutdown_event.is_set():
                self._ctx.logger.warn("Shutdown event detected, aborting compose wait.")
                # Check if coordinator container failed before returning
                try:
                    fqcn_shutdown = self._ctx.cluster.resource.fq_container_name(
                        "minitrino"
                    )
                    container_shutdown = self._ctx.cluster.resource.container(
                        fqcn_shutdown
                    )
                    if container_shutdown.status == "exited":
                        exit_code_shutdown = int(
                            container_shutdown.attrs.get("State", {}).get("ExitCode", 0)
                        )
                        if exit_code_shutdown != 0:
                            raise MinitrinoError(
                                "Failed to provision cluster. "
                                f"Coordinator container exited with code "
                                f"{exit_code_shutdown}."
                            )
                except NotFound:
                    pass
                return
            try:
                fqcn = self._ctx.cluster.resource.fq_container_name("minitrino")
                container = self._ctx.cluster.resource.container(fqcn)
                # Refresh container state to avoid checking stale/old containers
                container.reload()
                self._ctx.logger.debug(
                    f"Polling coordinator container: "
                    f"id={container.id[:12]}, status={container.status}"
                )

                # If we're expecting a container replacement (build/recreate),
                # skip checks on the old container
                if orig_container_id and container.id == orig_container_id:
                    self._ctx.logger.debug(
                        f"Still seeing old container (id={container.id[:12]}), "
                        "waiting for replacement..."
                    )
                    # Don't check logs on old container, wait for new one
                    time.sleep(0.5)
                    continue

                # If pre-start bootstraps complete, signal to workers
                # that they can safely provision
                if (
                    container.status == "running"
                    and b"- PRE START BOOTSTRAPS COMPLETED -" in container.logs()
                ):
                    self._worker_safe_event.set()
                # If any running container for fqcn, treat as success;
                # Wait for coordinator to actually be ready.
                if (
                    container.status == "running"
                    and b"- CLUSTER IS READY -" in container.logs()
                ):
                    if orig_container_id and container.id != orig_container_id:
                        self._ctx.logger.debug(
                            f"Coordinator container replaced: "
                            f"old id={orig_container_id[:12]}, "
                            f"new id={container.id[:12]}"
                        )
                    break
                # If current container is exited with nonzero exit code,
                # check if any newer running container exists
                if container.status == "exited":
                    exit_code = int(container.attrs.get("State", {}).get("ExitCode", 0))
                    if exit_code != 0:
                        # Check if a newer running container exists for fqcn
                        try:
                            container = self._ctx.cluster.resource.container(fqcn)
                            container.reload()
                            running_found = False
                            if container.status == "running":
                                self._ctx.logger.debug(
                                    f"Found newer running coordinator container: "
                                    f"id={container.id[:12]}"
                                )
                                running_found = True
                            if not running_found:
                                raise MinitrinoError(
                                    f"Coordinator container exited with code "
                                    f"{exit_code}."
                                )
                        except NotFound:
                            raise MinitrinoError(
                                f"Coordinator container exited with code {exit_code}."
                            ) from None
            except NotFound:
                pass

            if not compose_thread.is_alive() and not reset_timeout:
                try:
                    fqcn = self._ctx.cluster.resource.fq_container_name("minitrino")
                    container = self._ctx.cluster.resource.container(fqcn)
                    container.reload()

                    # If this is still the old container, wait for replacement
                    if orig_container_id and container.id == orig_container_id:
                        self._ctx.logger.debug(
                            f"Compose finished but still seeing old container "
                            f"(id={container.id[:12]}), waiting for replacement..."
                        )
                    else:
                        # New container exists, safe to reduce timeout
                        timeout = default_timeout
                        reset_timeout = True
                        self._ctx.logger.debug(
                            f"Compose thread finished and new container exists "
                            f"(id={container.id[:12]}), reducing coordinator wait "
                            f"timeout to {default_timeout} seconds."
                        )
                        self._ctx.logger.info(
                            "Waiting for coordinator container to start..."
                        )
                except NotFound:
                    # Container doesn't exist yet, likely still pulling
                    # image. Keep the original timeout and check again
                    # next iteration
                    self._ctx.logger.debug(
                        "Compose thread finished but container not found yet, "
                        "likely still pulling image. Maintaining original timeout."
                    )

            if time.time() - poll_start > timeout:
                raise MinitrinoError(
                    f"Timed out after {timeout} seconds waiting for "
                    "coordinator container to start."
                )
            time.sleep(1)

    def _set_license(self) -> None:
        """Set the license for the cluster."""
        if self._ctx.env.get("LIC_PATH"):
            user_provided_path = self._ctx.env["LIC_PATH"]
            self._ctx.logger.debug("License path provided. Ensuring absolute path.")
            try:
                self._ctx.env["LIC_PATH"] = os.path.abspath(
                    os.path.expanduser(user_provided_path)
                )
                assert os.path.isfile(self._ctx.env["LIC_PATH"])
            except Exception as e:
                raise UserError(
                    f"Failed to resolve valid license path: {e}",
                    f"Please provide a valid license path. "
                    f"Path provided: {user_provided_path}",
                ) from e

    def _determine_build(self) -> bool:
        """Determine if the image should be built."""
        # Check if image source has changed
        if self._image_src_changed():
            self._ctx.logger.debug(
                "Image source has changed. "
                "--build flag will be appended to compose command."
            )
            return True

        # Check if the image exists at all
        ver = self._ctx.env.get("CLUSTER_VER")
        dist = self._ctx.env.get("CLUSTER_DIST")
        image_tag = f"minitrino/cluster:{ver}-{dist}"

        try:
            self._ctx.docker_client.images.get(image_tag)
            self._ctx.logger.debug(f"Image {image_tag} exists, no build required.")
            return False
        except Exception:
            self._ctx.logger.debug(
                f"Image {image_tag} does not exist. "
                "--build flag will be appended to compose command."
            )
            return True

    @property
    def _image_src_checksum(self) -> str:
        """The checksum of the Minitrino image source directory."""
        if not hasattr(self, "_checksum"):
            self._checksum = self._get_image_src_checksum()
        return self._checksum

    def _get_image_src_checksum(self) -> str:
        """Return the checksum of the image source directory."""
        hashobj = hashlib.new("sha256")
        directory = os.path.join(self._ctx.lib_dir, "image")
        for root, _, files in os.walk(directory):
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                if not os.path.isfile(fpath) or os.path.islink(fpath):
                    continue
                # Include relative path in hash for uniqueness
                relpath = os.path.relpath(fpath, directory)
                hashobj.update(relpath.encode())
                with open(fpath, "rb") as f:
                    while chunk := f.read(8192):
                        hashobj.update(chunk)
        self._ctx.logger.debug(
            f"Minitrino image source current checksum: {hashobj.hexdigest()}"
        )
        return hashobj.hexdigest()

    def _image_src_changed(self) -> bool:
        """Compare current image source checksum to recorded checksum.

        If the image source checksum has not been recorded, always
        return True to force a build.

        Returns
        -------
        bool
            True if the image source has changed, False otherwise.
        """
        checksum = self._image_src_checksum
        ver = self._ctx.env.get("CLUSTER_VER")
        dist = self._ctx.env.get("CLUSTER_DIST")
        image_name = f"{ver}-{dist}"
        self._ctx.logger.debug(
            f"Checking if image source has changed for {image_name}..."
        )

        self.checksum_dir = os.path.join(
            self._ctx.minitrino_user_dir, ".imagechecksums"
        )
        if not os.path.isdir(self.checksum_dir):
            os.makedirs(self.checksum_dir)

        self.checksum_file = os.path.join(self.checksum_dir, f"{image_name}")
        if os.path.isfile(self.checksum_file):
            with open(self.checksum_file) as f:
                recorded_checksum = f.read().strip()
            self._ctx.logger.debug(
                f"Minitrino image source last recorded checksum "
                f"for image {image_name}: {recorded_checksum}"
            )
            return checksum != recorded_checksum
        else:
            return True

    def _record_image_src_checksum(self) -> None:
        """Record the image source checksum."""
        checksum = self._image_src_checksum
        self._ctx.logger.debug(
            f"Recording Minitrino image source checksum: "
            f"{checksum} to {self.checksum_file}"
        )
        with open(self.checksum_file, "w") as f:
            f.write(checksum)

    def _rollback(self) -> None:
        """Perform a cluster rollback."""
        if self.no_rollback:
            self._ctx.logger.warn(
                f"Errors occurred during cluster '{self._ctx.cluster_name}' "
                "provisioning and rollback has been disabled. "
                "Provisioned resources will remain in an unaltered state.",
            )
            return

        for cluster in self._ctx.provisioned_clusters:
            self._ctx.cluster_name = cluster  # Activate the cluster in the context
            self._ctx.cluster.ops.rollback()
