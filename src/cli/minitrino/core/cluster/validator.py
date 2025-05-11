#!/usr/bin/env python3

from __future__ import annotations

from minitrino.core.errors import UserError
from minitrino.settings import MIN_CLUSTER_VER, CLUSTER_CONFIG, CLUSTER_JVM_CONFIG

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext
    from minitrino.core.cluster.cluster import Cluster


class ClusterValidator:
    """
    Validates cluster configuration and environment variables.

    This class is responsible for validating cluster configuration and
    environment variables based on the current `MinitrinoContext`.

    Constructor Parameters
    ----------------------
    `ctx` : `MinitrinoContext`
        An instantiated `MinitrinoContext` object with user input and context.
    `cluster` : `Cluster`
        An instantiated `Cluster` object.

    Methods
    -------
    `check_cluster_ver()`
        Validates that the current `CLUSTER_VER` and `CLUSTER_DIST` environment
        variables meet minimum requirements for either Trino or Starburst
        distributions.
    `check_version_requirements(modules: Optional[list[str]] = None)`
        Validates cluster version compatibility against constraints defined in
        each module's `metadata.json`.
    `check_dependent_clusters(modules: Optional[list[str]] = None)`
        Identifies dependent clusters for the specified modules.
    `check_dup_config()`
        Checks for duplicate entries in `config.properties` and `jvm.config` and
        logs warnings if duplicates are found.
    """

    def __init__(self, ctx: MinitrinoContext, cluster: Cluster):
        self._ctx = ctx
        self._cluster = cluster

    def check_cluster_ver(self) -> None:
        """
        Validates that the current `CLUSTER_VER` and `CLUSTER_DIST` environment
        variables meet minimum requirements for either Trino or Starburst
        distributions.

        Raises
        ------
        `UserError`
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

    def check_version_requirements(self, modules: Optional[list[str]] = None) -> None:
        """
        Validates cluster version compatibility against constraints defined in
        each module's `metadata.json`.

        Parameters
        ----------
        `modules` : `list[str]`
            A list of module names to check version requirements for.

        Raises
        ------
        `UserError`
            If the version constraints are invalid or not satisfied.
        """

        modules = modules or []
        for module in modules:
            versions = self._ctx.modules.data.get(module, {}).get("versions", [])

            if not versions:
                continue
            if len(versions) > 2:
                raise UserError(
                    f"Invalid versions specification for module '{module}' in metadata.json file: {versions}",
                    f'The valid structure is: {{"versions": [min-ver, max-ver]}}. If the versions key is '
                    f"present, the minimum version is required, and the maximum version is optional.",
                )

            cluster_ver = int(self._ctx.env.get("CLUSTER_VER", "")[0:3])
            min_ver = int(versions.pop(0))
            max_ver = None
            if versions:
                max_ver = int(versions.pop())

            begin_msg = (
                f"The supplied cluster version {cluster_ver} is incompatible with module '{module}'. "
                f"Per the module's metadata.json file, the"
            )

            if cluster_ver < min_ver:
                raise UserError(
                    f"{begin_msg} minimum required cluster version for the module is: {min_ver}."
                )
            if max_ver and cluster_ver > max_ver:
                raise UserError(
                    f"{begin_msg} maximum required cluster version for the module is: {max_ver}."
                )

    def check_dependent_clusters(
        self, modules: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Identifies dependent clusters for the specified modules.

        Parameters
        ----------
        `modules` : `list[str]`
            A list of module names to check for dependencies.

        Returns
        -------
        `list[dict]`
            A list of cluster definitions that should be treated as
            dependencies.
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
        """
        Checks for duplicate entries in `config.properties` and `jvm.config` and
        logs warnings if duplicates are found.
        """

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
