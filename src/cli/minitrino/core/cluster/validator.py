"""Cluster validation utilities for Minitrino CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from minitrino.core.errors import UserError
from minitrino.settings import CLUSTER_CONFIG, CLUSTER_JVM_CONFIG, MIN_CLUSTER_VER

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
    check_cluster_ver()
        Validate that the current `CLUSTER_VER` and `CLUSTER_DIST`
        environment variables meet minimum requirements for either Trino
        or Starburst distributions.
    check_dependent_clusters(modules: Optional[list[str]] = None)
        Identify dependent clust
        ers for the specified modules.
    check_dup_config()
        Check for duplicate entries in `config.properties` and
        `jvm.config` and log warnings if duplicates are found.
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
                cluster_name = f"dep-cluster-{self._ctx.cluster_name}-{cluster['name']}"
                cluster["name"] = cluster_name
                dependent_clusters.append(cluster)

        for module in modules:
            module_data: dict = self._ctx.modules.data.get(module, {})
            module_dependent_clusters = module_data.get("dependentClusters", [])
            if module_dependent_clusters:
                _helper(module_dependent_clusters)

        for cluster in dependent_clusters:
            for module in cluster.get("modules", []):
                if module in modules:
                    raise UserError(
                        f"Circular dependency detected: Module {module} is both a "
                        f"dependency of cluster {self._ctx.cluster_name} and is "
                        "being provisioned."
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

        if cluster_cfgs is None or jvm_cfgs is None:
            current_cluster_cfgs, current_jvm_cfg = (
                self._cluster.config._current_config()
            )
            cluster_cfgs = cluster_cfgs or current_cluster_cfgs
            jvm_cfgs = jvm_cfgs or current_jvm_cfg
        log_duplicates(cluster_cfgs, CLUSTER_CONFIG)
        log_duplicates(jvm_cfgs, CLUSTER_JVM_CONFIG)
