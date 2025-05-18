"""Cluster validation utilities for Minitrino CLI."""

from __future__ import annotations

from minitrino.core.errors import UserError
from minitrino.settings import MIN_CLUSTER_VER, CLUSTER_CONFIG, CLUSTER_JVM_CONFIG

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext
    from minitrino.core.cluster.cluster import Cluster


class ClusterValidator:
    """
    Validate cluster configuration and environment variables.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and context.
    cluster : Cluster
        An instantiated `Cluster` object.

    Methods
    -------
    check_cluster_ver()
        Validate that the current `CLUSTER_VER` and `CLUSTER_DIST` environment variables
        meet minimum requirements for either Trino or Starburst distributions.
    check_dependent_clusters(modules: Optional[list[str]] = None)
        Identify dependent clusters for the specified modules.
    check_dup_config()
        Check for duplicate entries in `config.properties` and `jvm.config` and log
        warnings if duplicates are found.
    """

    def __init__(self, ctx: MinitrinoContext, cluster: Cluster):
        self._ctx = ctx
        self._cluster = cluster

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
            except:
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
            except:
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
            A list of cluster definitions that should be treated as dependencies.
        """
        self._ctx.logger.verbose("Checking for dependent clusters...")
        dependent_clusters = []
        modules = modules or []
        for module in modules:
            module_dependent_clusters = self._ctx.modules.data.get(module, {}).get(
                "dependentClusters", []
            )
            if module_dependent_clusters:
                for cluster in module_dependent_clusters:
                    cluster["name"] = f"module-dep-{cluster['name']}"
                    dependent_clusters.append(cluster)
        return list(dependent_clusters)

    def check_dup_config(self) -> None:
        """Check and warn for duplicate entries in cluster config files."""

        def log_duplicates(cfgs, filename):
            self._ctx.logger.verbose(
                f"Checking '{filename}' file for duplicate configs...",
            )

            unique: dict[str, list[list[str]]] = {}
            for cfg in cfgs:
                key = cfg[0]
                if key in unique:
                    unique[key].append(cfg)
                else:
                    unique[key] = [cfg]

            duplicates = ["=".join(x) for y in unique.values() for x in y if len(y) > 1]

            if duplicates:
                self._ctx.logger.warn(
                    f"Duplicate configuration properties detected in "
                    f"'{filename}' file:\n{str(duplicates)}",
                )

        current_cluster_cfgs, current_jvm_cfg = self._cluster.config._current_config()

        log_duplicates(current_cluster_cfgs, CLUSTER_CONFIG)
        log_duplicates(current_jvm_cfg, CLUSTER_JVM_CONFIG)
