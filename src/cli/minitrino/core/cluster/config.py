"""Configuration management for Minitrino clusters.

This module provides classes and functions to manage cluster
configuration files and settings for Minitrino, including writing config
files, setting ports, and handling user overrides.
"""

from __future__ import annotations

import os
import re
import socket
import time
from typing import TYPE_CHECKING, Optional

import yaml

from minitrino import utils
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

    def write_config(self, modules: Optional[list[str]] = None) -> None:
        """
        Append configs to cluster config files.

        Parameters
        ----------
        modules : list[str], optional
            A list of module names to include when collecting
            configuration overrides.
        """

        def handle_password_authenticators(cfgs):
            merge = []
            for i, cfg in enumerate(cfgs):
                if (
                    cfg[0] == "key_value"
                    and cfg[1] == "http-server.authentication.type"
                ):
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

        fq_container_name = self._cluster.resource.fq_container_name("minitrino")
        coordinator = self._cluster.resource.container(fq_container_name)

        if not coordinator:
            raise MinitrinoError(
                "Attempting to append cluster config in Minitrino container, "
                "but no running container was found."
            )

        cfgs = []
        jvm_cfg = []
        modules = modules or []
        modules.append("minitrino")  # check if user placed configs in root compose yaml

        # Check configs passed through env variables
        env_usr_cfgs = self._ctx.env.get("CONFIG_PROPERTIES", "")
        env_user_jvm_cfg = self._ctx.env.get("JVM_CONFIG", "")

        if env_usr_cfgs:
            cfgs.extend(self._split_config(env_usr_cfgs))
        if env_user_jvm_cfg:
            jvm_cfg.extend(self._split_config(env_user_jvm_cfg))

        # Check configs passed through Docker Compose YAMLs
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
                .get("CONFIG_PROPERTIES", [])
            )
            yaml_jvm_cfg = (
                yaml_file.get("services", {})
                .get("minitrino", {})
                .get("environment", {})
                .get("JVM_CONFIG", [])
            )

            if yaml_cfgs:
                cfgs.extend(self._split_config(yaml_cfgs))
            if yaml_jvm_cfg:
                jvm_cfg.extend(self._split_config(yaml_jvm_cfg))

        if not cfgs and not jvm_cfg:
            return

        cfgs = handle_password_authenticators(cfgs)

        self._ctx.logger.debug(
            "Checking coordinator server status before updating configs...",
        )

        retry = 0
        while retry <= 30:
            logs = coordinator.logs().decode()
            if "======== SERVER STARTED ========" in logs:
                self._ctx.logger.debug(
                    "Coordinator started.",
                )
                break
            elif coordinator.status != "running":
                raise MinitrinoError(
                    "The coordinator stopped running. Inspect the "
                    "container logs if the container is still available. "
                    "If the container was rolled back, rerun the command with "
                    "the '--no-rollback' option, then inspect the logs."
                )
            else:
                self._ctx.logger.debug(
                    "Waiting for coordinator to start...",
                )
                time.sleep(1)
                retry += 1

        def append_config(coordinator, usr_cfgs, current_cfgs, filename):
            """Replace overlapping config keys.

            Configs are sourced from user input (env variables or module
            docker compose YAML).
            """
            if not usr_cfgs:
                return

            user_kv = {}
            for entry in usr_cfgs:
                if entry[0] == "key_value":
                    k, v = entry[1], entry[2]
                    user_kv[k] = v

            used_keys = set()

            merged = []
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

            for entry in usr_cfgs:
                if entry[0] == "key_value":
                    k, v = entry[1], entry[2]
                    if k not in used_keys:
                        merged.append(("key_value", k, v))

            for entry in usr_cfgs:
                if entry[0] == "unified":
                    line = entry[1]
                    if line not in [e[1] for e in merged if e[0] == "unified"]:
                        merged.append(("unified", line))

            config_lines = []
            for entry in merged:
                if entry[0] == "key_value":
                    _, k, v = entry
                    config_lines.append(f"{k}={v}")
                elif entry[0] == "unified":
                    _, line = entry
                    config_lines.append(line)

            self._ctx.logger.debug(
                f"Removing existing {filename} file...",
            )
            self._ctx.cmd_executor.execute(
                f"bash -c 'rm {ETC_DIR}/{filename}'", container=coordinator
            )

            self._ctx.logger.debug(
                f"Writing new config to {filename}...\n",
                "Appending user-defined config to cluster container config...",
            )
            _, uid = utils.container_user_and_id(self._ctx, coordinator)
            for line in config_lines:
                append_cfg = f'bash -c "cat <<EOT >> {ETC_DIR}/{filename}\n{line}\nEOT"'
                self._ctx.cmd_executor.execute(
                    append_cfg,
                    container=coordinator,
                    suppress_output=True,
                    docker_user=uid,
                )

        current_cluster_cfgs, current_jvm_cfg = self._current_config()
        append_config(coordinator, cfgs, current_cluster_cfgs, CLUSTER_CONFIG)
        append_config(coordinator, jvm_cfg, current_jvm_cfg, CLUSTER_JVM_CONFIG)

        self._cluster.ops.restart_containers(
            [self._cluster.resource.fq_container_name("minitrino")]
        )

    def set_external_ports(self, modules: Optional[list[str]] = None) -> None:
        """
        Dynamically assign host ports to containers.

        Parameters
        ----------
        modules : list[str], optional
            A list of module names to scan for port mappings.
        """

        def is_port_in_use(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("0.0.0.0", port)) == 0

        def is_docker_port_in_use(port):
            containers = self._ctx.docker_client.containers.list()
            for container in containers:
                ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                for binding in ports.values():
                    if binding:
                        for b in binding:
                            if str(port) == b.get("HostPort"):
                                return True
            return False

        def find_next_available_port(default_port):
            candidate_port = default_port
            while is_port_in_use(candidate_port) or is_docker_port_in_use(
                candidate_port
            ):
                self._ctx.logger.debug(
                    f"Port {candidate_port} is already in use. "
                    "Finding the next available port..."
                )
                candidate_port += 1
            return candidate_port

        def assign_port(container_name, host_port_var, default_port):
            candidate_port = find_next_available_port(default_port)
            fq_container_name = self._cluster.resource.fq_container_name(container_name)
            self._ctx.logger.info(
                f"Found available port {candidate_port} for container "
                f"'{fq_container_name}'. The service can be reached at "
                f"localhost:{candidate_port}."
            )
            self._ctx.logger.debug(
                f"Setting environment variable {host_port_var} to " f"{candidate_port}"
            )
            self._ctx.env.update({host_port_var: str(candidate_port)})

        # Handle the core Minitrino container
        assign_port("minitrino", "__PORT_MINITRINO", 8080)

        # Handle module-defined services
        modules = modules or []
        services = self._ctx.modules.module_services(modules)
        for service in services:
            port_mappings = service[1].get("ports", [])
            container_name = service[1].get("container_name", "undefined")

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

                assign_port(container_name, host_port_var_name, int(default_port))

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
                parsed.append(("unified", cfg))
        return parsed

    def _current_config(self) -> tuple[list[tuple], list[tuple]]:
        """
        Fetch current cluster configs from the coordinator container.

        Returns
        -------
        tuple[list[tuple], list[tuple]]
            A tuple of parsed config tuples for both files.
        """
        fq_container_name = self._cluster.resource.fq_container_name("minitrino")
        _, uid = utils.container_user_and_id(self._ctx, fq_container_name)
        current_cfgs = self._ctx.cmd_executor.execute(
            f"bash -c 'cat {ETC_DIR}/{CLUSTER_CONFIG}'",
            f"bash -c 'cat {ETC_DIR}/{CLUSTER_JVM_CONFIG}'",
            container=self._cluster.resource.container(fq_container_name),
            suppress_output=True,
            docker_user=uid,
        )

        current_cluster_cfgs = self._split_config(current_cfgs[0].output)
        current_jvm_cfg = self._split_config(current_cfgs[1].output)

        return current_cluster_cfgs, current_jvm_cfg
