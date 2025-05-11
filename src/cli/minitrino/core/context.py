#!/usr/bin/env python3

import os
import re
import json
import docker

from minitrino import utils
from minitrino.core.cluster.cluster import Cluster
from minitrino.core.modules import Modules
from minitrino.core.envvars import EnvironmentVariables
from minitrino.core.cmd_exec import CommandExecutor
from minitrino.core.logger import MinitrinoLogger
from minitrino.core.errors import MinitrinoError, UserError

from pathlib import Path
from typing import cast, Optional


class MinitrinoContext:
    """
    Provides context and core controls that are globally accessible in command
    scripts. This class should not be instantiated from anywhere but the CLI's
    entrypoint, as it depends on user-provided inputs.

    Attributes
    ----------
    `logger` : `MinitrinoLogger`
        Logs CLI activity.
    `env` : `EnvironmentVariables`
        CLI environment variables, subdivided by sections.
    `modules` : `Modules`
        Metadata about Minitrino modules.
    `cmd_executor` : `CommandExecutor`
        Executes shell commands in host and containers.
    `docker_client` : `docker.DockerClient`
        Docker client for high-level API access.
    `api_client` : `docker.APIClient`
        Docker API client for low-level access.
    `all_clusters` : `bool`
        If True, operations are applied to all clusters.
    `verbose` : `bool`
        If True, enables verbose logging to stdout.
    `user_home_dir` : `str`
        Home directory of the current user.
    `minitrino_user_dir` : `str`
        Path to ~/.minitrino/ directory.
    `config_file` : `str`
        Path to user's minitrino.cfg file.
    `snapshot_dir` : `str`
        Path to snapshot directory for temporary tarballs.
    `lib_dir` : `str`
        Path to Minitrino's library directory.

    Methods
    -------
    `initialize(verbose: bool, user_env: Optional[list], cluster_name: str)` :
        Initializes attributes that depend on user-provided input.
    """

    def __init__(self):
        # Attributes that depend on user input prior to being set
        self.verbose = False
        self.all_clusters = False
        self.cluster_name = ""
        self.provisioned_clusters = []
        self._user_env = []

        self.cluster: Cluster = cast(Cluster, object())
        self.logger: MinitrinoLogger = cast(MinitrinoLogger, object())
        self.env: EnvironmentVariables = cast(EnvironmentVariables, object())
        self.modules: Modules = cast(Modules, object())
        self.cmd_executor: CommandExecutor = cast(CommandExecutor, object())
        self.docker_client: docker.DockerClient = cast(docker.DockerClient, object())
        self.api_client: docker.APIClient = cast(docker.APIClient, object())

        # Paths
        self.user_home_dir = os.path.expanduser("~")
        self.minitrino_user_dir = self._handle_minitrino_user_dir()
        self.config_file = self._config_file()
        self.snapshot_dir = os.path.join(self.minitrino_user_dir, "snapshots")
        self._lib_dir = None

    @utils.exception_handler
    def initialize(
        self,
        verbose: bool = False,
        user_env: Optional[list[str]] = None,
        cluster_name: str = "",
        version_only: bool = False,
    ) -> None:
        """
        Initializes core CLI context attributes.

        This method sets up logging, environment variables, and context-specific
        resources like the cluster and Docker clients. If `version_only` is
        True, initialization is limited to what is required to resolve the CLI
        and library versions.

        Parameters
        ----------
        `verbose` : `bool`, optional
            Enables verbose logging to stdout.
        `user_env` : `list[str]`, optional
            A list of user-provided environment variables.
        `cluster_name` : `str`, optional
            The cluster name to scope operations to. Defaults to "default".
        `version_only` : `bool`, optional
            If True, initializes only the attributes required for version
            fetching (e.g. `minitrino --version`).
        """

        self.verbose = verbose
        self._user_env = user_env or []

        self.logger = MinitrinoLogger(self.verbose)
        self.env = EnvironmentVariables(self)

        if version_only:
            return

        self._try_parse_library_env()
        self._compare_versions()

        self.modules = Modules(self)
        self.cmd_executor = CommandExecutor(self)
        self._set_cluster_attrs(cluster_name)
        self._set_docker_clients(env=self.env.copy())
        self.env._log_env_vars()

    @property
    def lib_dir(self) -> str:
        """
        Gets the library directory.

        The directory is determined using the following order of precedence:

        1. Use `LIB_PATH` if provided via environment (through `--env` option,
           OS environment variables, or the Minitrino config file).
        2. Check if the library exists relative to the location of the
           `components.py` file, assuming the project is running in a repository
           context.

        Returns
        -------
        `str`
            Path to the resolved library directory.
        """
        if not self._lib_dir:
            self._lib_dir = self._get_lib_dir()
        return self._lib_dir

    def _get_lib_dir(self) -> str:
        """
        Determines and validates the path to the Minitrino library directory.

        The method checks various potential locations for the `lib` directory,
        including a user-specified path, a default installation path, and a
        repository-relative path.

        Returns
        -------
        `str`
            Resolved library directory path.

        Raises
        ------
        `UserError`
            If a valid library cannot be found.
        """
        lib_dir = ""
        try:
            lib_dir = self.env.get("LIB_PATH", "")
        except:
            pass

        if not lib_dir and os.path.isdir(os.path.join(self.minitrino_user_dir, "lib")):
            lib_dir = os.path.join(self.minitrino_user_dir, "lib")
        elif not lib_dir:  # Use repo root, fail if this doesn't exist
            repo_root = Path(__file__).resolve().parents
            for parent in repo_root:
                if (parent / "src" / "lib").is_dir():
                    lib_dir = str(parent / "src" / "lib")
                    break

        if not os.path.isdir(lib_dir) or not os.path.isfile(
            os.path.join(lib_dir, "minitrino.env")
        ):
            raise UserError(
                "This operation requires a library to be installed.",
                f"The library can be installed in the default location (~/.minitrino/lib) "
                f"via the `lib-install` command, or it can be pointed to with the `LIB_PATH` "
                f"environment variable.",
            )

        self.logger.verbose(
            f"Library path set to: {lib_dir}",
        )
        return lib_dir

    def _handle_minitrino_user_dir(self) -> str:
        """
        Checks if a Minitrino directory exists in the user home directory. If it
        does not exist, the directory is created.

        Returns
        -------
        `str`
            Path to the Minitrino user home directory.
        """

        minitrino_user_dir = os.path.abspath(
            os.path.join(self.user_home_dir, ".minitrino")
        )
        if not os.path.isdir(minitrino_user_dir):
            os.mkdir(minitrino_user_dir)
        return minitrino_user_dir

    def _config_file(self) -> str:
        """
        Determines the path to the user's `minitrino.cfg` configuration file.

        If the file does not exist, a warning is issued but no exception is
        raised.

        Returns
        -------
        `str`
            Path to the configuration file.
        """

        config_file = os.path.join(self.minitrino_user_dir, "minitrino.cfg")
        if not os.path.isfile(config_file):
            self.logger.warn(
                f"No minitrino.cfg file found at {config_file}. "
                f"Run 'minitrino config' to reconfigure this file and directory.",
            )
        return config_file

    def _try_parse_library_env(self) -> None:
        """
        Attempts to parse the Minitrino library's `minitrino.env` file. If the
        file does not exist, it is silently skipped.
        """
        try:
            self.env._parse_library_env()
        except:  # Skip lib-related procedures if the lib is not found
            pass

    def _compare_versions(self) -> None:
        """
        Compares the CLI version with the library version and logs a warning if
        they do not match.
        """
        cli_ver = utils.cli_ver()
        lib_ver = utils.lib_ver(lib_path=self.lib_dir)
        if cli_ver != lib_ver:
            self.logger.warn(
                f"CLI version {cli_ver} and library version {lib_ver} "
                f"do not match. You can update the Minitrino library "
                f"version to match the CLI version by running 'minitrino "
                f"lib-install'.",
            )

    def _set_cluster_attrs(self, cluster_name: str) -> None:
        """
        Sets cluster attributes based on the active cluster name.
        """
        self._set_cluster_name(cluster_name)
        self.cluster = Cluster(self)
        self.env.update(
            {
                "COMPOSE_PROJECT_NAME": self.cluster.resource.compose_project_name(
                    self.cluster_name
                )
            }
        )

    def _set_cluster_name(self, cluster_name: str) -> None:
        """
        Determines and validates the active cluster name.

        Parameters
        ----------
        `cluster_name` : `str`
            The user-specified or default cluster name.
        """
        if cluster_name:
            self.cluster_name = cluster_name
        elif self.env.get("CLUSTER_NAME"):
            self.cluster_name = self.env.get("CLUSTER_NAME")
        else:
            self.cluster_name = "default"

        if self.cluster_name == "all":
            self.all_clusters = True

        if self.cluster_name == "images":
            raise UserError(
                "Cluster name 'images' is reserved for internal use. "
                "Please use a different cluster name."
            )

        if not re.fullmatch(r"[A-Za-z0-9_\-\*]+", self.cluster_name):
            raise UserError(
                f"Invalid cluster name '{self.cluster_name}'. Cluster names can only "
                f"contain alphanumeric characters, underscores, dashes, or asterisks "
                f"(asterisks are for filtering operations only and will not work with "
                f"the `provision` command)."
            )

        self.env.update({"CLUSTER_NAME": self.cluster_name})
        self.logger.verbose(f"Cluster name set to: {self.cluster_name}")

    def _set_docker_clients(self, env: Optional[dict] = None) -> None:
        """
        Initializes Docker clients for both high-level and low-level API access.

        Parameters
        ----------
        `env` : `dict`, optional
            Dictionary of environment variables used when resolving the current
            Docker context. Defaults to an empty dictionary.

        Raises
        ------
        `MinitrinoError`
            If the Docker socket file cannot be determined.
        """
        if env is None:
            env = {}

        self.logger.verbose(
            "Attempting to locate Docker socket file for current Docker context..."
        )

        try:
            output = self.cmd_executor.execute(
                "docker context inspect", environment=env, suppress_output=True
            )
            context = json.loads(output[0].get("output", ""))[0]
            socket = context["Endpoints"]["docker"].get("Host", "")
        except Exception as e:
            raise MinitrinoError(
                f"Failed to locate Docker socket file. Error: {str(e)}"
            )

        self.logger.verbose(
            f"Docker socket file for current context '{context['Name']}' located at: {socket}"
        )

        try:
            docker_client = docker.DockerClient(base_url=socket)
            api_client = docker.APIClient(base_url=socket)
            self.docker_client, self.api_client = docker_client, api_client
        except:
            self.docker_client = cast(docker.DockerClient, object())
            self.api_client = cast(docker.APIClient, object())
