"""Configuration management for Minitrino clusters.

This module provides classes and functions to manage cluster
configuration files and settings for Minitrino, including writing config
files, setting ports, and handling user overrides.
"""

from __future__ import annotations

import os
import re
import socket
from typing import TYPE_CHECKING, Optional

import yaml

from minitrino import utils
from minitrino.core.docker.wrappers import MinitrinoContainer
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.settings import (
    CLUSTER_CONFIG,
    CLUSTER_JVM_CONFIG,
    ETC_DIR,
)

if TYPE_CHECKING:
    from minitrino.core.cluster.cluster import Cluster
    from minitrino.core.context import MinitrinoContext


class ClusterConfigManager:
    """
    Manage cluster configuration for the current cluster.

    This class handles reading, writing, and updating configuration
    files for Minitrino clusters, including dynamic port assignment and
    user overrides.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and
        context.
    cluster : Cluster
        An instantiated `Cluster` object.
    """

    def __init__(self, ctx: MinitrinoContext, cluster: Cluster):
        self._ctx = ctx
        self._cluster = cluster

    def write_config(
        self,
        modules: Optional[list[str]] = None,
        coordinator: bool = False,
        worker: bool = False,
        workers: int = 0,
    ) -> None:
        """
        Append configs to cluster config files.

        Parameters
        ----------
        modules : list[str], optional
            A list of module names to include when collecting
            configuration overrides.
        coordinator : bool
            Whether to write configs to the coordinator container.
        worker : bool
            Whether to write configs to the worker containers.
        workers : int
            The number of workers being provisioned.
        """

        def _check_container(fq_full_name: str) -> MinitrinoContainer:
            cluster_container = self._cluster.resource.container(fq_full_name)
            if not cluster_container:
                raise MinitrinoError(
                    f"Attempting to append cluster config in Minitrino container "
                    f"'{fq_full_name}', but no running container was found."
                )
            return cluster_container

        if coordinator:
            coordinator_container = _check_container(
                self._cluster.resource.fq_container_name("minitrino")
            )
            self._write_config_to_container(
                modules, False, workers, coordinator_container
            )

        if worker and workers > 0:
            for worker_id in range(1, workers + 1):
                worker_container = _check_container(
                    self._cluster.resource.fq_container_name(
                        f"minitrino-worker-{worker_id}"
                    )
                )
                self._write_config_to_container(
                    modules, True, workers, worker_container
                )

    def set_external_ports(self, modules: Optional[list[str]] = None) -> None:
        """
        Dynamically assign host ports to containers.

        Parameters
        ----------
        modules : list[str], optional
            A list of module names to scan for port mappings.
        """
        self._assign_port("minitrino", "__PORT_MINITRINO", 8080)

        modules = modules or []
        services = self._ctx.modules.module_services(modules)
        for service in services:
            port_mappings = service[1].get("ports", [])
            container_name = service[1].get("container_name", "undefined")
            if container_name == "undefined":
                # If the container name is undefined, use the service name
                container_name = service[0]
            for port_mapping in port_mappings:
                if "__PORT" not in port_mapping:
                    continue
                host_port_var, default_port = port_mapping.split(":")
                # Remove ${} syntax from the environment variable name
                host_port_var_name = re.sub(r"\$\{([^}]+)\}", r"\1", host_port_var)
                try:
                    isinstance(int(default_port), int)
                except ValueError as e:
                    raise UserError(
                        f"Default port '{default_port}' is not a valid integer. "
                        f"Please check the module's Docker Compose YAML file for the "
                        f"correct variable name and ensure a default value is "
                        f"set as an environment variable. See the wiki for more "
                        f"information: TODO: link\n{e}",
                    )
                self._assign_port(container_name, host_port_var_name, int(default_port))

    def _get_user_configs(
        self, modules: Optional[list[str]], worker: bool = False
    ) -> tuple[list, list]:
        """
        Collect user and module config and JVM config overrides.

        Defaults to collecting coordinator configs. Optionally collects
        worker configs if `worker` is `True`.
        """
        cfgs = []
        jvm_cfg = []
        modules = modules or []
        modules = list(modules) + ["minitrino"]  # ensure minitrino is checked

        if worker:
            jvm_env_var = "JVM_CONFIG_WORKER"
            config_env_var = "CONFIG_PROPERTIES_WORKER"
        else:
            jvm_env_var = "JVM_CONFIG"
            config_env_var = "CONFIG_PROPERTIES"

        env_usr_cfgs = self._ctx.env.get(config_env_var, "")
        env_user_jvm_cfg = self._ctx.env.get(jvm_env_var, "")
        if env_usr_cfgs:
            cfgs.extend(self._split_config(env_usr_cfgs))
        if env_user_jvm_cfg:
            jvm_cfg.extend(self._split_config(env_user_jvm_cfg))

        for module in modules:
            if module == "minitrino":
                with open(os.path.join(self._ctx.lib_dir, "docker-compose.yaml")) as f:
                    yaml_file = yaml.load(f, Loader=yaml.FullLoader)
            else:
                yaml_file = self._ctx.modules.data.get(module, {}).get("yaml_dict")
            yaml_cfgs = (
                yaml_file.get("services", {})
                .get("minitrino", {})
                .get("environment", {})
                .get(config_env_var, [])
            )
            yaml_jvm_cfg = (
                yaml_file.get("services", {})
                .get("minitrino", {})
                .get("environment", {})
                .get(jvm_env_var, [])
            )
            if yaml_cfgs:
                cfgs.extend(self._split_config(yaml_cfgs))
            if yaml_jvm_cfg:
                jvm_cfg.extend(self._split_config(yaml_jvm_cfg))
        return cfgs, jvm_cfg

    def _handle_password_authenticators(self, cfgs):
        """Merge multiple password authenticators."""
        merge = []
        for i, cfg in enumerate(cfgs):
            if cfg[0] == "key_value" and cfg[1] == "http-server.authentication.type":
                merge.append(i)
        if not merge:
            return cfgs
        values = [cfgs[i][2].upper() for i in merge]
        auth_property = (
            "key_value",
            "http-server.authentication.type",
            ",".join(values),
        )
        new_cfgs = [x for i, x in enumerate(cfgs) if i not in merge]
        new_cfgs.append(auth_property)
        return new_cfgs

    def _append_config(self, coordinator, usr_cfgs, current_cfgs, filename):
        """Write merged config to the container."""
        if not usr_cfgs:
            return
        user_kv = {}
        # Convert user config to dict for easy lookup
        for entry in usr_cfgs:
            if entry[0] == "key_value":
                k, v = entry[1], entry[2]
                user_kv[k] = v
        used_keys = set()
        merged = []
        # Merge user config with current config
        for entry in current_cfgs:
            if entry[0] == "key_value":
                key, _ = entry[1], entry[2]
                if key in user_kv:
                    merged.append(("key_value", key, user_kv[key]))
                    used_keys.add(key)
                else:
                    merged.append(entry)
            else:
                merged.append(entry)
        # Add any unused user config
        for entry in usr_cfgs:
            if entry[0] == "key_value":
                k, v = entry[1], entry[2]
                if k not in used_keys:
                    merged.append(("key_value", k, v))
        # Add any unused unified config
        for entry in usr_cfgs:
            if entry[0] == "unified":
                line = entry[1]
                if line not in [e[1] for e in merged if e[0] == "unified"]:
                    merged.append(("unified", line, ""))
        config_lines = []
        for entry in merged:
            # Convert merged config to lines for I/O
            if entry[0] == "key_value":
                _, k, v = entry
                config_lines.append(f"{k}={v}")
            elif entry[0] == "unified":
                _, line, _ = entry
                config_lines.append(line)
        self._ctx.logger.debug(f"Removing existing {filename} file...")
        self._ctx.cmd_executor.execute(
            f"bash -c 'rm {ETC_DIR}/{filename}'", container=coordinator
        )
        self._ctx.logger.debug(
            f"Writing new config to {filename}...\n",
            "Appending user-defined config to cluster container config...",
        )
        _, uid = utils.container_user_and_id(self._ctx, coordinator)
        for line in config_lines:
            append_cfg = f"bash -c \"cat <<'EOT' >> {ETC_DIR}/{filename}\n{line}\nEOT\""
            self._ctx.cmd_executor.execute(
                append_cfg,
                container=coordinator,
                docker_user=uid,
            )

    def _split_config(self, cfgs: str = "") -> list[tuple]:
        """
        Split raw config strings into an ordered list of tuples.

        Each tuple is either ('key_value', key, value) or ('unified',
        line). Preserves the original ordering and comments.
        """
        cfgs_list = cfgs.strip().split("\n")
        parsed = []
        for cfg in cfgs_list:
            cfg = re.sub(r"\s*=\s*", "=", cfg)
            parts = cfg.split("=", 1)
            if len(parts) == 2:
                parsed.append(("key_value", parts[0], parts[1]))
            else:
                parsed.append(("unified", cfg, ""))
        return parsed

    def _current_config(
        self, container: MinitrinoContainer
    ) -> tuple[list[tuple], list[tuple]]:
        """
        Fetch current cluster configs from a cluster container.

        Parameters
        ----------
        container : MinitrinoContainer
            The container to fetch configs from.

        Returns
        -------
        tuple[list[tuple], list[tuple]]
            A tuple of parsed config tuples for both files.
        """
        _, uid = utils.container_user_and_id(self._ctx, container)
        current_cfgs = self._ctx.cmd_executor.execute(
            f"bash -c 'cat {ETC_DIR}/{CLUSTER_CONFIG}'",
            f"bash -c 'cat {ETC_DIR}/{CLUSTER_JVM_CONFIG}'",
            container=container,
            suppress_output=True,
            docker_user=uid,
        )

        current_cluster_cfgs = self._split_config(current_cfgs[0].output)
        current_jvm_cfg = self._split_config(current_cfgs[1].output)

        return current_cluster_cfgs, current_jvm_cfg

    def _write_config_to_container(
        self,
        modules: Optional[list[str]] = None,
        worker: bool = False,
        workers: int = 0,
        cluster_container: MinitrinoContainer = None,
    ):
        """Write config to a cluster container."""
        modules = modules or []
        self._ctx.logger.debug(f"Writing config to container: {cluster_container.name}")
        cfgs, jvm_cfg = self._get_user_configs(modules, worker)

        # Inject node-scheduler.include-coordinator=false for
        # coordinator if workers > 0, but only if user did NOT
        # explicitly set it to true via env
        if not worker and workers > 0:
            user_env_cfg = self._ctx.env.get("CONFIG_PROPERTIES", "")
            user_explicit_true = any(
                line.strip() == "node-scheduler.include-coordinator=true"
                for line in user_env_cfg.splitlines()
            )
            if not user_explicit_true:
                # Remove any existing key to avoid duplicates
                cfgs = [
                    c
                    for c in cfgs
                    if not (
                        c[0] == "key_value"
                        and c[1] == "node-scheduler.include-coordinator"
                    )
                ]
                cfgs.append(
                    ("key_value", "node-scheduler.include-coordinator", "false")
                )

        if not cfgs and not jvm_cfg:
            self._signal_append_config_complete(cluster_container)
            return

        cfgs = self._handle_password_authenticators(cfgs)

        current_cluster_cfgs, current_jvm_cfg = self._current_config(cluster_container)
        self._append_config(
            cluster_container, cfgs, current_cluster_cfgs, CLUSTER_CONFIG
        )
        self._append_config(
            cluster_container, jvm_cfg, current_jvm_cfg, CLUSTER_JVM_CONFIG
        )
        self._signal_append_config_complete(cluster_container)

    def _signal_append_config_complete(self, container: MinitrinoContainer):
        """Signal that configs have been appended."""
        _, uid = utils.container_user_and_id(self._ctx, container)
        self._ctx.cmd_executor.execute(
            f"bash -c 'echo FINISHED > {ETC_DIR}/.minitrino/append-config-status.txt'",
            container=container,
            docker_user=uid,
        )

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use on the local machine."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("0.0.0.0", port)) == 0

    def _is_docker_port_in_use(self, port: int) -> bool:
        """Check if a port is in use by any running Docker container."""
        containers = self._ctx.docker_client.containers.list()
        for container in containers:
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            for binding in ports.values():
                if binding:
                    for b in binding:
                        if str(port) == b.get("HostPort"):
                            return True
        return False

    def _find_next_available_port(self, default_port: int) -> int:
        """Find the next available port on the host."""
        candidate_port = default_port
        while self._is_port_in_use(candidate_port) or self._is_docker_port_in_use(
            candidate_port
        ):
            self._ctx.logger.debug(
                f"Port {candidate_port} is already in use. "
                "Finding the next available port..."
            )
            candidate_port += 1
        return candidate_port

    def _assign_port(
        self, container_name: str, host_port_var: str, default_port: int
    ) -> None:
        """Assign an available host port to a container."""
        candidate_port = self._find_next_available_port(default_port)
        fq_container_name = self._cluster.resource.fq_container_name(container_name)
        self._ctx.logger.info(
            f"Found available port {candidate_port} for container '"
            f"{fq_container_name}'. The service can be reached at "
            f"localhost:{candidate_port}.",
        )
        self._ctx.logger.debug(
            f"Setting environment variable {host_port_var} to {candidate_port}"
        )
        self._ctx.env.update({host_port_var: str(candidate_port)})
