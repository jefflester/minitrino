"""Cluster validation utilities for Minitrino CLI."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from minitrino import utils
from minitrino.core.docker.wrappers import MinitrinoContainer
from minitrino.core.errors import UserError
from minitrino.settings import (
    CLUSTER_CONFIG,
    CLUSTER_JVM_CONFIG,
    ETC_DIR,
    MIN_CLUSTER_VER,
)

if TYPE_CHECKING:
    from minitrino.core.cluster.cluster import Cluster
    from minitrino.core.context import MinitrinoContext


class ClusterValidator:
    """
    Validate cluster configuration and environment variables.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and
        context.
    cluster : Cluster
        An instantiated `Cluster` object.

    Methods
    -------
    check_cluster_name()
        Validate that the cluster name is valid.
    check_cluster_ver()
        Validate that the current `CLUSTER_VER` and `CLUSTER_DIST`
        environment variables meet minimum requirements for either Trino
        or Starburst distributions.
    check_dependent_clusters(modules: Optional[list[str]] = None)
        Identify dependent clusters for the specified modules.
    check_dup_config()
        Check for duplicate entries in `config.properties` and
        `jvm.config` and log warnings if duplicates are found.
    """

    def __init__(self, ctx: MinitrinoContext, cluster: Cluster):
        self._ctx = ctx
        self._cluster = cluster

    def check_cluster_name(self) -> None:
        """
        Validate that the cluster name is valid.

        Raises
        ------
        UserError
            If the cluster name is invalid.
        """
        if self._ctx.cluster_name == "images" or self._ctx.cluster_name == "system":
            raise UserError(
                f"Cluster name '{self._ctx.cluster_name}' is reserved for "
                "internal use. Please use a different cluster name."
            )

        if not re.fullmatch(r"[A-Za-z0-9_\-\*]+", self._ctx.cluster_name):
            raise UserError(
                f"Invalid cluster name '{self._ctx.cluster_name}'. Cluster names can "
                "only contain alphanumeric characters, underscores, dashes, or "
                "asterisks (asterisks are for filtering operations only and will "
                "not work with the `provision` command)."
            )

    def check_cluster_ver(self) -> None:
        """
        Validate that the cluster version meets minimum requirements.

        Raises
        ------
        UserError
            If the provided version is too low or formatted incorrectly.
        """
        cluster_dist = self._ctx.env.get("CLUSTER_DIST", "")
        cluster_ver = self._ctx.env.get("CLUSTER_VER", "")

        if cluster_dist == "starburst":
            error_msg = (
                f"Provided Starburst version '{cluster_ver}' is invalid. "
                f"The version must be {MIN_CLUSTER_VER}-e or higher."
            )
            try:
                cluster_ver_int = int(cluster_ver[0:3])
                if cluster_ver_int < MIN_CLUSTER_VER or "-e" not in cluster_ver:
                    raise UserError(error_msg)
            except Exception:
                raise UserError(error_msg)
        elif cluster_dist == "trino":
            error_msg = (
                f"Provided Trino version '{cluster_ver}' is invalid. "
                f"The version must be {MIN_CLUSTER_VER} or higher."
            )
            if "-e" in cluster_ver:
                raise UserError(
                    f"The provided Trino version '{cluster_ver}' cannot contain '-e'. "
                    "Did you mean to use Starburst via the --image option?"
                )
            try:
                cluster_ver_int = int(cluster_ver[0:3])
                if cluster_ver_int < MIN_CLUSTER_VER:
                    raise UserError(error_msg)
            except Exception:
                raise UserError(error_msg)

    def check_dependent_clusters(
        self, modules: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Identify dependent clusters for the specified modules.

        Parameters
        ----------
        modules : list[str]
            A list of module names to check for dependencies.

        Returns
        -------
        list[dict]
            A list of cluster definitions that should be treated as
            dependencies.
        """
        self._ctx.logger.debug("Checking for dependent clusters...")
        dependent_clusters = []
        modules = modules or []

        def _helper(module_dependent_clusters):
            for cluster in module_dependent_clusters:
                cluster_name = f"{self._ctx.cluster_name}-dep-{cluster['name']}"
                cluster["name"] = cluster_name
                dependent_clusters.append(cluster)

        for module in modules:
            module_data: dict = self._ctx.modules.data.get(module, {})
            module_dependent_clusters = module_data.get("dependentClusters", [])
            if module_dependent_clusters:
                _helper(module_dependent_clusters)

        # Circular dependency check: dependent clusters cannot list
        # their parent module as a dependency (would cause infinite
        # recursion)
        for parent_module in modules:
            parent_module_data: dict = self._ctx.modules.data.get(parent_module, {})
            module_dependent_clusters = parent_module_data.get("dependentClusters", [])
            for cluster in module_dependent_clusters:
                cluster_modules = cluster.get("modules", [])
                if parent_module in cluster_modules:
                    raise UserError(
                        f"Circular dependency detected: Dependent cluster "
                        f"'{cluster.get('name', 'unknown')}' of module "
                        f"'{parent_module}' cannot list '{parent_module}' "
                        "as one of its modules. This would cause infinite "
                        "recursion during provisioning."
                    )

        return list(dependent_clusters)

    def check_dup_config(self, cluster_cfgs=None, jvm_cfgs=None) -> None:
        """Check for duplicate entries in cluster config files."""

        def log_duplicates(cfgs, filename):
            self._ctx.logger.debug(
                f"Checking '{filename}' file for duplicate configs...",
            )

            unique: dict[str, list[list[str]]] = {}
            for cfg in cfgs:
                if cfg[0] == "key_value":
                    key = cfg[1]  # config property name
                elif cfg[0] == "unified":
                    key = cfg[1]  # unified line itself
                else:
                    key = str(cfg)
                if key in unique:
                    unique[key].append(cfg)
                else:
                    unique[key] = [cfg]

            duplicates = {k: v for k, v in unique.items() if len(v) > 1}
            if duplicates:
                msg = [
                    f"Duplicate configuration properties detected in '{filename}' file:"
                ]
                for key, entries in duplicates.items():
                    msg.append(f"  {key}:")
                    for entry in entries:
                        if entry[0] == "key_value":
                            msg.append(f"    - {entry[1]}={entry[2]}")
                        elif entry[0] == "unified":
                            msg.append(f"    - {entry[1]}")
                        else:
                            msg.append(f"    - {entry}")
                self._ctx.logger.warn("\n".join(msg))

        containers = self._cluster.resource.cluster_containers()
        for container in containers:
            if cluster_cfgs is None or jvm_cfgs is None:
                current_cluster_cfgs, current_jvm_cfg = self._current_config(container)
                cluster_cfgs = cluster_cfgs or current_cluster_cfgs
                jvm_cfgs = jvm_cfgs or current_jvm_cfg
            log_duplicates(cluster_cfgs, CLUSTER_CONFIG)
            log_duplicates(jvm_cfgs, CLUSTER_JVM_CONFIG)

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
            [f"cat {ETC_DIR}/{CLUSTER_CONFIG}"],
            [f"cat {ETC_DIR}/{CLUSTER_JVM_CONFIG}"],
            container=container,
            suppress_output=True,
            user=uid,
        )

        current_cluster_cfgs = self._split_config(current_cfgs[0].output)
        current_jvm_cfg = self._split_config(current_cfgs[1].output)

        return current_cluster_cfgs, current_jvm_cfg

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
