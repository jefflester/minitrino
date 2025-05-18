"""Module management for Minitrino CLI."""

from __future__ import annotations

import os
import json
import yaml

from minitrino import utils
from minitrino.core.errors import MinitrinoError, UserError

from minitrino.settings import (
    COMPOSE_LABEL_KEY,
    LIC_VOLUME_MOUNT,
    LIC_MOUNT_PATH,
    DUMMY_LIC_MOUNT_PATH,
    MODULE_ROOT,
    MODULE_ADMIN,
    MODULE_SECURITY,
    MODULE_CATALOG,
    MODULE_LABEL_KEY,
)

from typing import cast, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class Modules:
    """
    Module validation and management for Minitrino CLI.

    This class is responsible for loading, storing, and exposing metadata about
    available Minitrino modules based on the current `MinitrinoContext`.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and context.

    Attributes
    ----------
    data : dict
        A dictionary of loaded module metadata keyed by module name.

    Methods
    -------
    running_modules() :
        Returns a dictionary of modules that are currently running.
    check_dep_modules(modules: Optional[list[str]] = None) :
        Check if provided modules have dependencies and include them.
    check_module_version_requirements(modules: Optional[list[str]] = None) :
        Check module version compatibility against the provided cluster version.
    check_compatibility(modules: Optional[list[str]] = None) :
        Check for mutually exclusive modules among the provided modules.
    check_enterprise(modules: Optional[list[str]] = None) :
        Check if any provided modules are Starburst Enterprise features and validate
        license.
    module_services(modules: Optional[list[str]] = None) :
        Get all services defined in the provided modules.
    check_volumes(modules: Optional[list[str]] = None) :
        Check if any of the provided modules have persistent volumes and warn the user.
    """

    def __init__(self, ctx: MinitrinoContext) -> None:
        self.data: dict = {}
        self._ctx = ctx
        self._load_modules()

    def running_modules(self) -> dict[str, str]:
        """
        Retrieve running modules by inspecting active Docker containers.

        Returns
        -------
        dict[str, str]
            A dictionary mapping module names (lowercase strings) to their associated
            cluster name.

        Raises
        ------
        UserError
            If any container lacks expected Minitrino labels or if a running module is
            not found in the loaded library data.

        Notes
        -----
        This method inspects active Docker containers for the current cluster and
        extracts module names and their associated cluster from Docker labels. Only
        containers with valid `org.minitrino` labels are considered modules.
        """
        utils.check_daemon(self._ctx.docker_client)

        categories = [f"{MODULE_ADMIN}-", f"{MODULE_CATALOG}-", f"{MODULE_SECURITY}-"]
        resources = self._ctx.cluster.resource.resources()
        containers = resources.containers()

        if not containers:
            return {}

        modules = {}
        hint_msg = "Check the compose.yaml file for this module at %s"
        for container in containers:
            labels = container.labels or {}
            cluster_name = labels.get(COMPOSE_LABEL_KEY)
            if cluster_name:
                cluster_name = cluster_name.replace("minitrino-", "")

            found_module_label = False
            for label_key, label_val in labels.items():
                if "org.minitrino" not in label_key:
                    continue
                for category in categories:
                    if category in label_val:
                        module = label_val.lower().replace(category, "")
                        if cluster_name is None:
                            raise UserError(
                                f"Unable to determine cluster name for container '{container.name}'. "
                                f"Container '{container.name}' is either missing the '{COMPOSE_LABEL_KEY}' "
                                f"label or it is malformed.",
                                hint_msg=hint_msg.format(
                                    self.data.get(module, {}).get(
                                        "yaml_file", "<unknown>"
                                    )
                                ),
                            )
                        modules[module] = cluster_name
                        found_module_label = True

            if not found_module_label and not (
                "minitrino-worker" in str(container.name)
                or container.name == f"minitrino-{cluster_name}"
            ):
                raise UserError(
                    f"Missing Minitrino labels for container '{container.name}'.",
                    hint_msg=hint_msg.format(
                        self.data.get(module, {}).get("yaml_file", "<unknown>")
                    ),
                )

        for module in modules:
            if not isinstance(self.data.get(module), dict):
                raise UserError(
                    f"Module '{module}' is running, but it is not found "
                    f"in the library. Was it deleted, or are you pointing "
                    f"Minitrino to the wrong location?"
                )
        return modules

    def check_dep_modules(self, modules: Optional[list[str]] = None) -> list[str]:
        """
        Check if provided modules have dependencies and include them.

        Parameters
        ----------
        modules : Optional[list[str]]
            List of module names to check. Default is `None`.

        Returns
        -------
        list[str]
            List of modules dependent to the modules provided.
        """
        if modules is None:
            modules = []

        for module in modules:
            dependent_modules = self.data.get(module, {}).get("dependentModules", [])
            if not dependent_modules:
                continue
            for dependent_module in dependent_modules:
                if dependent_module not in modules:
                    modules.insert(0, dependent_module)
                    self._ctx.logger.verbose(
                        f"Module dependency for module '{module}' will be included: '{dependent_module}'",
                    )
        return list(set(modules))

    def check_module_version_requirements(
        self, modules: Optional[list[str]] = None
    ) -> None:
        """
        Check module version compatibility against the provided cluster version.

        Parameters
        ----------
        modules : list[str]
            A list of module names to check version requirements for.

        Raises
        ------
        UserError
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

    def check_compatibility(self, modules: Optional[list[str]] = None) -> None:
        """
        Check for mutually exclusive modules among the provided modules.

        Parameters
        ----------
        modules : Optional[list[str]]
            List of module names to check. Default is `None`.

        Raises
        ------
        UserError
            If incompatible modules are detected.
        """
        if modules is None:
            modules = []

        for module in modules:
            incompatible = self.data.get(module, {}).get("incompatibleModules", [])
            if not incompatible:
                continue
            for module_inner in modules:
                if (module_inner in incompatible) or (
                    incompatible[0] == "*" and len(modules) > 1
                ):
                    raise UserError(
                        f"Incompatible modules detected. Tried to provision module "
                        f"'{module_inner}', but found that the module is incompatible "
                        f"with module '{module}'. Incompatible modules listed for module "
                        f"'{module}' are: {incompatible}",
                        f"You can see which modules are incompatible with this module by "
                        f"running 'minitrino modules -m {module}'",
                    )

    def check_enterprise(self, modules: Optional[list[str]] = None) -> None:
        """
        Check for Starburst Enterprise modules and validate license.

        Parameters
        ----------
        modules : Optional[list[str]]
            List of module names to check. Default is `None`.

        Raises
        ------
        UserError
            If a required license is missing.
        """
        if modules is None:
            modules = []

        self._ctx.logger.verbose(
            "Checking for Starburst Enterprise modules...",
        )

        yaml_path = os.path.join(self._ctx.lib_dir, "docker-compose.yaml")
        with open(yaml_path) as f:
            yaml_file = yaml.load(f, Loader=yaml.FullLoader)
        volumes = yaml_file.get("services", {}).get("minitrino", {}).get("volumes", [])

        if LIC_VOLUME_MOUNT not in volumes:
            raise UserError(
                f"The required license volume in the library's root docker-compose.yaml "
                f"is either commented out or deleted: {yaml_path}. For reference, "
                f"the proper volume mount is: '{LIC_VOLUME_MOUNT}'"
            )

        enterprise_modules = []
        for module in modules:
            if self.data.get(module, {}).get("enterprise", False):
                enterprise_modules.append(module)

        if enterprise_modules:
            if not self._ctx.env.get("CLUSTER_DIST") == "starburst":
                raise UserError(
                    f"Module(s) {enterprise_modules} are only compatible with "
                    f"Starburst Enterprise. Please specify the image type with the '-i' option. "
                    f"Example: `minitrino provision -i starburst`",
                )
            if not self._ctx.env.get("LIC_PATH", False):
                raise UserError(
                    f"Module(s) {enterprise_modules} requires a Starburst license. "
                    f"You must provide a path to a Starburst license via the "
                    f"LIC_PATH environment variable."
                )
            self._ctx.env.update({"LIC_MOUNT_PATH": LIC_MOUNT_PATH})
        elif self._ctx.env.get("LIC_PATH", False):
            self._ctx.env.update({"LIC_MOUNT_PATH": LIC_MOUNT_PATH})
        else:
            self._ctx.env.update({"LIC_PATH": "./modules/resources/dummy.license"})
            self._ctx.env.update({"LIC_MOUNT_PATH": DUMMY_LIC_MOUNT_PATH})

    def module_services(self, modules: Optional[list[str]] = None) -> list[list]:
        """
        Get all services defined in the provided modules.

        Parameters
        ----------
        modules : Optional[list[str]]
            List of module names to retrieve services from. Default is `None`.

        Returns
        -------
        list[list]
            List of services, each as a list containing the service key (`str`), service
            dictionary (`dict`), and the YAML file path (`str`).

        Raises
        ------
        MinitrinoError
            If a module's Docker Compose YAML file lacks a 'services' section.
        """
        if modules is None:
            modules = []

        services = []
        for module in modules:
            yaml_file = self.data.get(module, {}).get("yaml_file", "")
            module_services = (
                self.data.get(module, {}).get("yaml_dict", {}).get("services", {})
            )
            if not module_services:
                raise MinitrinoError(
                    f"Invalid Docker Compose YAML file (no 'services' section found): {yaml_file}"
                )
            # Get all services defined in YAML file
            for service_key, service_dict in module_services.items():
                services.append([service_key, service_dict, yaml_file])

        return services

    def check_volumes(self, modules: Optional[list[str]] = None) -> None:
        """
        Check for persistent volumes and warn the user if any are found.

        Parameters
        ----------
        modules : Optional[list[str]]
            List of module names to check. Default is `None`.
        """
        if modules is None:
            modules = []

        self._ctx.logger.verbose(
            "Checking modules for persistent volumes...",
        )

        for module in modules:
            if self.data.get(module, {}).get("yaml_dict", {}).get("volumes", {}):
                self._ctx.logger.warn(
                    f"Module '{module}' has persistent volumes associated with it. "
                    f"To delete these volumes, remember to run `minitrino remove --volumes`.",
                )

    def _load_modules(self) -> None:
        """
        Load module data during class instantiation.

        Raises
        ------
        MinitrinoError
            If the resolved `modules_dir` path is not a directory.

        UserError
            If a module is missing its expected `.yaml` file.

        Notes
        -----
        This method scans the Minitrino library for valid module directories under the
        `admin`, `catalog`, and `security` sections. Each module must include a matching
        `.yaml` file, and may optionally include a `metadata.json` file. Parsed module
        information is stored in the `data` attribute.
        """
        self._ctx.logger.verbose("Loading modules...")

        modules_dir = os.path.join(self._ctx.lib_dir, MODULE_ROOT)
        if not os.path.isdir(modules_dir):
            raise MinitrinoError(
                f"Path is not a directory: {modules_dir}. "
                f"Are you pointing to a compatible Minitrino library?"
            )

        # Loop through all module types
        sections = [
            os.path.join(modules_dir, MODULE_ADMIN),
            os.path.join(modules_dir, MODULE_CATALOG),
            os.path.join(modules_dir, MODULE_SECURITY),
        ]

        for section_dir in sections:
            for _dir in os.listdir(section_dir):
                module_dir = os.path.join(section_dir, _dir)

                if not os.path.isdir(module_dir):
                    self._ctx.logger.verbose(
                        f"Skipping file (expected a directory, not a file) "
                        f"at path: {module_dir}",
                    )
                    continue

                # List inner-module files
                module_files = os.listdir(module_dir)

                yaml_basename = f"{os.path.basename(module_dir)}.yaml"
                if yaml_basename not in module_files:
                    raise UserError(
                        f"Missing Docker Compose file in module directory {_dir}. "
                        f"Expected file to be present: {yaml_basename}",
                        hint_msg="Check this module in your library to ensure it is properly constructed.",
                    )

                # Module dir and YAML exist, add to modules
                module_name = os.path.basename(module_dir)
                self.data[module_name] = {}
                self.data[module_name]["type"] = os.path.basename(section_dir)
                self.data[module_name]["module_dir"] = module_dir

                # Add YAML file path
                yaml_file = os.path.join(module_dir, yaml_basename)
                self.data[module_name]["yaml_file"] = yaml_file

                # Add YAML dict
                with open(yaml_file) as f:
                    self.data[module_name]["yaml_dict"] = yaml.load(
                        f, Loader=yaml.FullLoader
                    )

                # Get metadata.json if present
                json_basename = "metadata.json"
                json_file = os.path.join(module_dir, json_basename)
                metadata = {}
                if os.path.isfile(json_file):
                    with open(json_file) as f:
                        metadata = json.load(f)
                else:
                    self._ctx.logger.verbose(
                        f"No JSON metadata file for module '{module_name}'. "
                        f"Will not load metadata for module.",
                    )
                for k, v in metadata.items():
                    self.data[module_name][k] = v

                # Add module label
                self.data[module_name][
                    "label"
                ] = f"{MODULE_LABEL_KEY}={self.data[module_name]['type']}-{module_name}"
