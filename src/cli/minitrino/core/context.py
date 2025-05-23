"""Core context and controls for Minitrino CLI."""

import os
import re
from pathlib import Path
from typing import Optional, cast

import docker

from minitrino import utils
from minitrino.core.cluster.cluster import Cluster
from minitrino.core.cmd_exec import CommandExecutor
from minitrino.core.docker.socket import resolve_docker_socket
from minitrino.core.envvars import EnvironmentVariables
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.logger import LogLevel, MinitrinoLogger
from minitrino.core.modules import Modules


class MinitrinoContext:
    """
    Expose context and core controls to CLI scripts.

    Attributes
    ----------
    cluster : Cluster
        Cluster interface.
    logger : MinitrinoLogger
        Logs CLI activity.
    env : EnvironmentVariables
        CLI environment variables, subdivided by sections.
    modules : Modules
        Metadata about Minitrino modules.
    cmd_executor : CommandExecutor
        Executes shell commands in host and containers.
    docker_client : docker.DockerClient
        Docker client for high-level API access.
    api_client : docker.APIClient
        Docker API client for low-level access.
    all_clusters : bool
        If True, operations are applied to all clusters.
    user_home_dir : str
        Home directory of the current user.
    minitrino_user_dir : str
        Path to ~/.minitrino/ directory.
    config_file : str
        Path to user's minitrino.cfg file.
    snapshot_dir : str
        Path to snapshot directory for temporary tarballs.
    lib_dir : str
        Path to Minitrino's library directory.

    Methods
    -------
    initialize()
        Hydrate the context with user-provided inputs.
    """

    cluster: Cluster
    logger: MinitrinoLogger
    env: EnvironmentVariables
    modules: Modules
    cmd_executor: CommandExecutor
    docker_client: docker.DockerClient
    api_client: docker.APIClient
    all_clusters: bool
    provisioned_clusters: list[str]
    user_home_dir: str
    minitrino_user_dir: str
    config_file: str
    snapshot_dir: str
    lib_dir: str

    def __init__(self):
        # ------------------------------
        # ---- User-provided inputs ----
        self._log_level = LogLevel.INFO
        self._user_env = []
        self.cluster_name = "default"
        # ------------------------------

        self.all_clusters = False
        self.provisioned_clusters = []

        self.logger = MinitrinoLogger()
        self.cluster: Optional[Cluster] = None
        self.env: Optional[EnvironmentVariables] = None
        self.modules: Optional[Modules] = None
        self.cmd_executor: Optional[CommandExecutor] = None
        self.docker_client: Optional[docker.DockerClient] = None
        self.api_client: Optional[docker.APIClient] = None

        self.user_home_dir = os.path.expanduser("~")
        self.minitrino_user_dir = self._handle_minitrino_user_dir()
        self.config_file = self._config_file()
        self.snapshot_dir = os.path.join(self.minitrino_user_dir, "snapshots")
        self._lib_dir = None

        self._initialized = False

    @utils.exception_handler
    def initialize(
        self,
        log_level: Optional[LogLevel] = None,
        user_env: Optional[list[str]] = None,
        cluster_name: str = "",
        version_only: bool = False,
    ) -> None:
        """
        Initialize core CLI context attributes.

        This method sets up logging, environment variables, and
        context-specific resources like the cluster and Docker clients.
        If `version_only` is True, initialization is limited to what is
        required to resolve the CLI and library versions.

        Parameters
        ----------
        log_level : LogLevel, optional
            Minimum log level to emit (default: INFO)
        user_env : list[str], optional
            A list of user-provided environment variables.
        cluster_name : str, optional
            The cluster name to scope operations to. Defaults to
            "default".
        version_only : bool, optional
            If True, initializes only the attributes required for
            version fetching (e.g. `minitrino --version`).
        """
        if self._initialized:
            raise MinitrinoError("Context has already been initialized.")

        if isinstance(log_level, LogLevel):
            self._log_level = log_level
        self.logger = MinitrinoLogger(self._log_level)
        self.env = EnvironmentVariables(self)
        if version_only:
            return
        self._logged_config_file_missing = False
        self._validate_config_file()
        self._try_parse_library_env()
        self._compare_versions()
        self.modules = Modules(self)
        self.cmd_executor = CommandExecutor(self)
        if cluster_name:
            self._set_cluster_attrs(cluster_name)
        else:
            self._set_cluster_attrs(self.cluster_name)
        self._set_docker_clients(env=self.env.copy())
        self.env._log_env_vars()
        self._initialized = True

    @property
    def lib_dir(self) -> str:
        """
        Get the library directory.

        Returns
        -------
        str
            Path to the resolved library directory.

        Notes
        -----
        The directory is determined using the following order of
        precedence:

        1. Use `LIB_PATH` if provided via environment.
        2. Check if the library exists relative to the location of this
           file,
        assuming the project is running in a repository context.
        """
        if not self._lib_dir:
            self._lib_dir = self._get_lib_dir()
        return self._lib_dir

    def _get_lib_dir(self) -> str:
        """
        Determine and validate the path to the library directory.

        Returns
        -------
        str
            Resolved library directory path.

        Raises
        ------
        UserError
            If a valid library cannot be found.
        """
        lib_dir = ""
        try:
            lib_dir = self.env.get("LIB_PATH", "")
        except Exception:
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
                "The library can be installed in the default location "
                "(~/.minitrino/lib) via the lib-install command, or it "
                "can be pointed to with the LIB_PATH environment variable.",
            )

        self.logger.debug(
            f"Library path set to: {lib_dir}",
        )
        return lib_dir

    def _handle_minitrino_user_dir(self) -> str:
        """
        Create the `~/.minitrino` directory if not exists.

        Returns
        -------
        str
            Path to the user's `~/.minitrino` directory.
        """
        minitrino_user_dir = os.path.abspath(
            os.path.join(self.user_home_dir, ".minitrino")
        )
        if not os.path.isdir(minitrino_user_dir):
            try:
                os.mkdir(minitrino_user_dir)
            except Exception as e:
                raise UserError(
                    "Failed to create the minitrino user directory.",
                    str(e),
                )
        return minitrino_user_dir

    def _validate_config_file(self) -> None:
        """Validate the path to the user's `minitrino.cfg` file."""
        config_file = os.path.join(self.minitrino_user_dir, "minitrino.cfg")
        if not os.path.isfile(config_file):
            msg = (
                f"No minitrino.cfg file found at {config_file}. Run "
                "'minitrino config' to reconfigure this file and directory."
            )
            if not self._logged_config_file_missing:
                self.logger.warn(msg)
                self._logged_config_file_missing = True

    def _config_file(self) -> str:
        """
        Return the path to the user's `minitrino.cfg` file.

        Returns
        -------
        str
            Path to the user's `minitrino.cfg` file.
        """
        config_file = os.path.join(self.minitrino_user_dir, "minitrino.cfg")
        return config_file

    def _try_parse_library_env(self) -> None:
        """Attempt to parse the library environment file if present."""
        try:
            self.env._parse_library_env()
        except Exception:  # Skip lib-related procedures if the lib is not found
            pass

    def _compare_versions(self) -> None:
        """Compare CLI and library versions for compatibility."""
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
        Set cluster-related attributes for the context.

        Parameters
        ----------
        cluster_name : str
            The name of the cluster to set.
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
        Determine and validate the active cluster name.

        Parameters
        ----------
        cluster_name : str
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
        self.logger.debug(f"Cluster name set to: {self.cluster_name}")

    def _set_docker_clients(self, env: Optional[dict] = None) -> None:
        """
        Initialize Docker clients.

        Parameters
        ----------
        env : dict, optional
            Dictionary of environment variables used when resolving the
            current Docker context. Defaults to an empty dictionary.

        Raises
        ------
        MinitrinoError
            If the Docker socket file cannot be determined.
        """
        self.logger.debug(
            "Attempting to locate Docker socket file for current Docker context..."
        )
        try:
            socket = resolve_docker_socket(self, env)
            self.logger.debug(f"Docker socket path: {socket}")
            docker_client = docker.DockerClient(base_url=socket)
            api_client = docker.APIClient(base_url=socket)
            self.docker_client, self.api_client = docker_client, api_client
        except Exception:
            self.docker_client = cast(docker.DockerClient, object())
            self.api_client = cast(docker.APIClient, object())
