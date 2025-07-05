"""Cluster operations and resource management for Minitrino clusters."""

from __future__ import annotations

import hashlib
import os
import shutil
import threading
import time
from typing import TYPE_CHECKING, Optional

from docker.errors import NotFound

from minitrino import utils
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.shutdown import shutdown_event

if TYPE_CHECKING:
    from minitrino.core.cluster.cluster import Cluster
    from minitrino.core.context import MinitrinoContext


class ClusterProvisioner:
    """
    Provision the cluster and provided modules.

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

    def provision(
        self,
        modules: list[str],
        image: str,
        workers: int,
        no_rollback: bool,
    ) -> None:
        """
        Provision the cluster and provided modules.

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
            self._ensure_shared_network()
            self._runner()

            dependent_clusters = self._ctx.cluster.validator.check_dependent_clusters(
                self.modules
            )
            for cluster in dependent_clusters:
                self._runner(cluster=cluster)

            self._record_image_src_checksum()
            self._ctx.logger.info("Environment provisioning complete.")

        try:
            _orchestrate()
        except Exception as e:
            crashdump = os.path.join(self._ctx.minitrino_user_dir, "crashdump.log")
            with open(crashdump, "w") as f:
                for msg, _, is_spinner in self._ctx.logger._log_sink.buffer:
                    if not is_spinner:
                        f.write(msg + "\n")
            raise MinitrinoError(f"{str(e)}\nFull provision log written to {crashdump}")

    def _runner(self, cluster: Optional[dict] = None) -> None:
        """
        Execute the provisioning sequence for a cluster and modules.

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

        self._set_env_vars()
        self._ctx.provisioned_clusters.append(self._ctx.cluster_name)

        self._ctx.modules.check_enterprise()
        self._ctx.modules.check_compatibility()
        self._ctx.modules.check_volumes()
        self._ctx.cluster.ports.set_external_ports()

        try:
            module_yaml_paths = self._module_yaml_paths()
            compose_cmd = self._build_compose_command(module_yaml_paths)
            self._run_compose_and_wait(compose_cmd)

            if self.workers > 0:
                with self._ctx.logger.spinner(
                    f"Provisioning {self.workers} workers..."
                ):
                    self._ctx.cluster.ops.reconcile_workers(self.workers)
                    self._ctx.logger.info(
                        f"{self.workers} workers provisioned successfully."
                    )

            self._ctx.cluster.validator.check_dup_config()

        except Exception as e:
            self._rollback()
            raise MinitrinoError("Failed to provision cluster.", e)

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

    def _append_running_modules(self, modules: Optional[list[str]] = None) -> list[str]:
        """
        Add running modules to the modules list.

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
        """
        Return a list of YAML file paths for enabled modules.

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
        """
        Resolve the Docker Compose executable and base command.

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
        self, module_yaml_paths: Optional[list[str]] = None
    ) -> list[str]:
        """
        Build the Docker Compose command as a list of arguments.

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
        """
        Run the compose command asynchronously.

        Parameters
        ----------
        compose_cmd : list[str]
            The docker compose command to execute (as a list of
            arguments).
        """
        if "COMPOSE_BAKE" not in self._ctx.env:
            self._ctx.env["COMPOSE_BAKE"] = "true"

        self._compose_failed = threading.Event()
        self._compose_error: Optional[BaseException] = None

        def _run_compose() -> None:
            try:
                for line in self._ctx.cmd_executor.stream_execute(
                    compose_cmd, environment=self._ctx.env.copy(), suppress_output=True
                ):
                    self._ctx.logger.debug(line)
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
                )
            finally:
                compose_thread.join()

    def _wait_for_coordinator_container(
        self,
        orig_container_id: str | None,
        compose_thread: threading.Thread,
    ) -> None:
        """
        Wait for the coordinator container to be running.

        Parameters
        ----------
        orig_container_id : str | None
            ID of the original coordinator container.
        compose_thread : threading.Thread
            Thread running the compose command.
        """
        timeout = (
            int(self._ctx.env.get("PROVISION_BUILD_TIMEOUT", 1200))
            if self.build
            else 30
        )
        default_timeout = 30
        reset_timeout = False
        poll_start = time.time()
        while True:
            if self._compose_failed.is_set():
                msg = "Docker Compose command failed."
                raise MinitrinoError(msg, self._compose_error)
            if shutdown_event.is_set():
                self._ctx.logger.warn("Shutdown event detected, aborting compose wait.")
                return
            try:
                fqcn = self._ctx.cluster.resource.fq_container_name("minitrino")
                container = self._ctx.cluster.resource.container(fqcn)
                self._ctx.logger.debug(
                    f"Polling coordinator container: "
                    f"id={container.id}, status={container.status}"
                )
                # If any running container for fqcn, treat as success
                if container.status == "running":
                    if orig_container_id and container.id != orig_container_id:
                        self._ctx.logger.debug(
                            f"Coordinator container replaced: "
                            f"old id={orig_container_id}, new id={container.id}"
                        )
                    break
                # If current container is exited with nonzero exit code,
                # check if any newer running container exists
                if container.status == "exited":
                    exit_code = int(container.attrs.get("State", {}).get("ExitCode", 0))
                    if exit_code != 0:
                        # Check if a newer running container exists for fqcn
                        container = self._ctx.cluster.resource.container(fqcn)
                        running_found = False
                        if container.status == "running":
                            self._ctx.logger.debug(
                                f"Found newer running coordinator container: "
                                f"id={container.id}"
                            )
                            running_found = True
                        if not running_found:
                            raise MinitrinoError(
                                f"Coordinator container exited with code {exit_code}."
                            )
            except NotFound:
                pass

            if not compose_thread.is_alive() and not reset_timeout:
                timeout = default_timeout
                reset_timeout = True
                self._ctx.logger.debug(
                    f"Compose thread finished, reducing "
                    f"coordinator wait timeout to {default_timeout} seconds."
                )
                self._ctx.logger.info("Waiting for coordinator container to start...")

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
                )

    def _determine_build(self) -> bool:
        """Determine if the image should be built."""
        if self._image_src_changed():
            self._ctx.logger.debug(
                "Image source has changed. "
                "--build flag will be appended to compose command."
            )
            return True
        return False

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
        """
        Compare current image source checksum to recorded checksum.

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
            with open(self.checksum_file, "r") as f:
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
