"""Port management for Minitrino clusters.

This module provides classes and functions to manage port assignments for Minitrino
clusters, including dynamic port assignment and handling user overrides.
"""

from __future__ import annotations

import re
import socket
from typing import TYPE_CHECKING

from minitrino.core.errors import UserError

if TYPE_CHECKING:
    from minitrino.core.cluster.cluster import Cluster
    from minitrino.core.context import MinitrinoContext


class ClusterPortManager:
    """Manage cluster ports for the current cluster.

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

    def set_external_ports(self, modules: list[str] | None = None) -> None:
        """Dynamically assign host ports to containers.

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
                # If the container name is undefined, use the service
                # name
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
                    ) from e
                self._assign_port(container_name, host_port_var_name, int(default_port))

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use on the local machine."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return False
            except OSError:
                return True

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

    def _find_next_available_port(
        self, default_port: int, exclude_var: str | None = None
    ) -> int:
        """Find the next available port on the host."""
        candidate_port = default_port
        while (
            self._is_port_in_use(candidate_port)
            or self._is_docker_port_in_use(candidate_port)
            or self._is_port_assigned_in_session(candidate_port, exclude_var)
        ):
            self._ctx.logger.debug(
                f"Port {candidate_port} is already in use. "
                "Finding the next available port..."
            )
            candidate_port += 1
        return candidate_port

    def _is_port_assigned_in_session(
        self, port: int, exclude_var: str | None = None
    ) -> bool:
        """Check if a port has been assigned in the current session."""
        for env_var, env_value in self._ctx.env.items():
            if env_var.startswith("__PORT_") and env_value == str(port):
                if exclude_var and env_var == exclude_var:
                    continue  # Skip the variable we're currently assigning
                return True
        return False

    def _assign_port(
        self, container_name: str, host_port_var: str, default_port: int
    ) -> None:
        """Assign an available host port to a container."""
        candidate_port = self._find_next_available_port(default_port, host_port_var)
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
