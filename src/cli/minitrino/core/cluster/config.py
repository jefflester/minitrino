#!/usr/bin/env python3

from __future__ import annotations

import os
import re
import time
import yaml
import socket

from minitrino.core.cmd_exec import CommandResult
from minitrino.core.errors import MinitrinoError, UserError

from minitrino.settings import (
    CLUSTER_CONFIG,
    CLUSTER_JVM_CONFIG,
    ETC_DIR,
)

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext
    from minitrino.core.cluster.cluster import Cluster


class ClusterConfigManager:
    """
    Cluster configuration manager for the current cluster.

    Constructor Parameters
    ----------------------
    `ctx` : `MinitrinoContext`
        An instantiated `MinitrinoContext` object with user input and context.
    `cluster` : `Cluster`
        An instantiated `Cluster` object.

    Methods
    -------
    `write_config(modules: Optional[list[str]] = None)`
        Appends user- and/or module-specified configurations to
        `config.properties` and `jvm.config` in the coordinator container,
        restarting it if updates occur.
    `set_external_ports(modules: Optional[list[str]] = None)`
        Dynamically assigns host ports for Minitrino and module containers that
        expose services on default or user-defined ports.
    """

    def __init__(self, ctx: MinitrinoContext, cluster: Cluster):
        self._ctx = ctx
        self._cluster = cluster

    def write_config(self, modules: Optional[list[str]] = None) -> None:
        """
        Appends user- and/or module-specified configurations to
        `config.properties` and `jvm.config` in the coordinator container,
        restarting it if updates occur.

        Parameters
        ----------
        `modules` : `list[str]`
            A list of module names to include when collecting configuration
            overrides.
        """

        def handle_password_authenticators(cfgs):
            merge = []
            for i, cfg in enumerate(cfgs):
                if cfg[0] == "http-server.authentication.type":
                    merge.append(i)

            if not merge:
                return cfgs

            auth_property = "http-server.authentication.type="
            for i, cfg in enumerate(merge):
                if i + 1 == len(merge):
                    auth_property += cfgs[cfg][1].upper()
                else:
                    auth_property += f"{cfgs[cfg][1].upper()},"

            cfgs = [x for i, x in enumerate(cfgs) if i not in merge]
            parts = auth_property.split("=", 1)
            if len(parts) == 2:
                key, val = parts
                cfgs.append([key, val])
            else:
                raise UserError(f"Invalid auth property: {auth_property}")
            return cfgs

        fq_container_name = self._cluster.resource.fq_container_name("minitrino")
        coordinator = self._cluster.resource.container(fq_container_name)

        if not coordinator:
            raise MinitrinoError(
                f"Attempting to append cluster config in Minitrino container, "
                f"but no running container was found."
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
            usr_cfgs = (
                yaml_file.get("services", {})
                .get("minitrino", {})
                .get("environment", {})
                .get("CONFIG_PROPERTIES", [])
            )
            user_jvm_cfg = (
                yaml_file.get("services", {})
                .get("minitrino", {})
                .get("environment", {})
                .get("JVM_CONFIG", [])
            )

            if usr_cfgs:
                cfgs.extend(self._split_config(usr_cfgs))
            if user_jvm_cfg:
                jvm_cfg.extend(self._split_config(user_jvm_cfg))

        if not cfgs and not jvm_cfg:
            return

        cfgs = handle_password_authenticators(cfgs)

        self._ctx.logger.verbose(
            "Checking coordinator server status before updating configs...",
        )

        retry = 0
        while retry <= 30:
            logs = coordinator.logs().decode()
            if "======== SERVER STARTED ========" in logs:
                self._ctx.logger.verbose(
                    "Coordinator started.",
                )
                break
            elif coordinator.status != "running":
                raise MinitrinoError(
                    f"The coordinator stopped running. Inspect the container logs if the "
                    f"container is still available. If the container was rolled back, rerun "
                    f"the command with the '--no-rollback' option, then inspect the logs."
                )
            else:
                self._ctx.logger.verbose(
                    "Waiting for coordinator to start...",
                )
                time.sleep(1)
                retry += 1

        def append_config(coordinator, usr_cfgs, current_cfgs, filename):
            """If there is an overlapping config key, replace it with the user
            config."""

            if not usr_cfgs:
                return

            current_cfgs = [
                cfg
                for cfg in current_cfgs
                if not any(cfg[0] == usr_cfg[0] for usr_cfg in usr_cfgs)
            ]

            current_cfgs.extend(usr_cfgs)
            current_cfgs = ["=".join(x) for x in current_cfgs]

            self._ctx.logger.verbose(
                f"Removing existing {filename} file...",
            )
            self._ctx.cmd_executor.execute(
                f"bash -c 'rm {ETC_DIR}/{filename}'", container=coordinator
            )

            self._ctx.logger.verbose(
                f"Writing new config to {filename}...",
            )
            for current_cfg in current_cfgs:
                append_cfg = (
                    f'bash -c "cat <<EOT >> {ETC_DIR}/{filename}\n{current_cfg}\nEOT"'
                )
                self._ctx.cmd_executor.execute(
                    append_cfg, container=coordinator, suppress_output=True
                )

        self._ctx.logger.verbose(
            "Appending user-defined config to cluster container config...",
        )

        current_cluster_cfgs, current_jvm_cfg = self._current_config()
        append_config(coordinator, cfgs, current_cluster_cfgs, CLUSTER_CONFIG)
        append_config(coordinator, jvm_cfg, current_jvm_cfg, CLUSTER_JVM_CONFIG)

        self._cluster.ops.restart_containers(
            [self._cluster.resource.fq_container_name("minitrino")]
        )

    def set_external_ports(self, modules: Optional[list[str]] = None) -> None:
        """
        Dynamically assigns host ports for Minitrino and module containers that
        expose services on default or user-defined ports.

        Parameters
        ----------
        `modules` : `list[str]`
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
                self._ctx.logger.verbose(
                    f"Port {candidate_port} is already in use. Finding the next available port..."
                )
                candidate_port += 1
            return candidate_port

        def assign_port(container_name, host_port_var, default_port):
            candidate_port = find_next_available_port(default_port)
            fq_container_name = self._cluster.resource.fq_container_name(container_name)
            self._ctx.logger.info(
                f"Found available port {candidate_port} for container '{fq_container_name}'. "
                f"The service can be reached at localhost:{candidate_port}."
            )
            self._ctx.logger.verbose(
                f"Setting environment variable {host_port_var} to {candidate_port}"
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
                if not "__PORT" in port_mapping:
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

    def _split_config(self, cfgs: str = "") -> list[list[str]]:
        """
        Splits raw config strings into key-value pairs.

        Parameters
        ----------
        `cfgs` : `str`
            Multi-line string of key=value pairs.

        Returns
        -------
        `list[list[str]]`
            List of [key, value] pairs.
        """
        cfgs_list = cfgs.strip().split("\n")
        parsed_cfgs = []
        for cfg in cfgs_list:
            cfg = re.sub(r"\s*=\s*", "=", cfg)
            parts = cfg.split("=", 1)
            if len(parts) == 2:
                key, val = parts
                parsed_cfgs.append([key, val])
        return parsed_cfgs

    def _current_config(self) -> tuple[list[list[str]], list[list[str]]]:
        """
        Fetches current contents of `config.properties` and `jvm.config` from
        the Minitrino coordinator container.

        Returns
        -------
        `tuple[list[list[str]], list[list[str]]]`
            A tuple of parsed key-value config lists for both files.
        """
        fq_container_name = self._cluster.resource.fq_container_name("minitrino")
        current_cfgs: list[CommandResult] = self._ctx.cmd_executor.execute(
            f"bash -c 'cat {ETC_DIR}/{CLUSTER_CONFIG}'",
            f"bash -c 'cat {ETC_DIR}/{CLUSTER_JVM_CONFIG}'",
            container=self._cluster.resource.container(fq_container_name),
            suppress_output=True,
        )

        current_cluster_cfgs = self._split_config(current_cfgs[0].get("output", ""))
        current_jvm_cfg = self._split_config(current_cfgs[1].get("output", ""))

        return current_cluster_cfgs, current_jvm_cfg
