"""Core context and controls for Minitrino CLI."""

import contextlib
import logging
import os
from pathlib import Path
from typing import cast

import docker

from minitrino import utils
from minitrino.core.cluster.cluster import Cluster
from minitrino.core.docker.socket import resolve_docker_socket
from minitrino.core.envvars import EnvironmentVariables
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.exec.cmd import CommandExecutor
from minitrino.core.library import LibraryManager
from minitrino.core.logging.levels import LogLevel
from minitrino.core.logging.logger import MinitrinoLogger
from minitrino.core.modules import Modules


class MinitrinoContext:
    """Expose context and core controls to CLI scripts.

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

    Notes
    -----
    The `lib_dir` property cannot be accessed prior to `_lib_safe` being
    set to `True`, which occurs early during `initialize()`. The idea is
    to force any user-provided env vars (since one of them may be
    `LIB_PATH`) to load before we attempt to do anything with the
    library.
    """

    cluster: Cluster
    logger: MinitrinoLogger
    env: EnvironmentVariables
    modules: Modules
    cmd_executor: CommandExecutor
    docker_client: docker.DockerClient | None
    api_client: docker.APIClient | None
    library_manager: LibraryManager
    all_clusters: bool
    provisioned_clusters: list[str]
    user_home_dir: str
    minitrino_user_dir: str
    config_file: str
    snapshot_dir: str

    def __init__(self):
        # ------------------------------
        # ---- User-provided inputs ----
        self.cluster_name = "default"
        self._user_env_args = []
        self._user_log_level = LogLevel.INFO
        # ------------------------------

        self.all_clusters = False
        self.provisioned_clusters = []

        self.logger: MinitrinoLogger = logging.getLogger("minitrino")
        self.cluster: Cluster | None = None
        self.env: EnvironmentVariables | None = None
        self.modules: Modules | None = None
        self.cmd_executor: CommandExecutor | None = None
        self.docker_client: docker.DockerClient | None = None
        self.api_client: docker.APIClient | None = None
        self.lib_manager = LibraryManager(self)

        self.user_home_dir = os.path.expanduser("~")
        self.minitrino_user_dir = self._handle_minitrino_user_dir()
        self.config_file = self._config_file()
        self.snapshot_dir = os.path.join(self.minitrino_user_dir, "snapshots")
        self._lib_dir = None

        # State
        self._initialized = False
        self._lib_safe = False
        self._logged_config_file_missing = False

    @utils.exception_handler
    def initialize(
        self,
        cluster_name: str = "",
        version_only: bool = False,
        log_level: LogLevel | None = None,
    ) -> None:
        """Initialize core CLI context attributes.

        This method sets up logging, environment variables, and
        context-specific resources like the cluster and Docker clients.
        If `version_only` is True, initialization is limited to what is
        required to resolve the CLI and library versions.

        Parameters
        ----------
        cluster_name : str, optional
            The cluster name to scope operations to. Defaults to
            "default".
        version_only : bool, optional
            If True, initializes only the attributes required for
            version fetching (e.g. `minitrino --version`).
        log_level : LogLevel, optional
            The log level to set for the logger.
        """
        if self._initialized:
            raise MinitrinoError("Context has already been initialized.")
        self._lib_safe = True
        self.env = EnvironmentVariables(self)
        if version_only:
            return
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
        if log_level:
            self.logger.set_level(log_level)
        self._initialized = True

    @property
    def user_log_level(self) -> LogLevel:
        """The user-configured log level for this context.

        Immutable once set.

        Returns
        -------
        LogLevel
            The immutable log level set by the user or default (INFO).
        """
        return self._user_log_level

    @user_log_level.setter
    def user_log_level(self, value: LogLevel) -> None:
        """Set the user log level once. Further attempts to set will raise.

        Parameters
        ----------
        value : LogLevel
            The log level to set.

        Raises
        ------
        RuntimeError
            If the log level has already been set to a non-default
            value.
        """
        if self._user_log_level != LogLevel.INFO:
            raise MinitrinoError("user_log_level is immutable once set.")
        self._user_log_level = value

    @property
    def lib_dir(self) -> str:
        """Get the library directory.

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
           file, assuming the project is running in a repository context.
        """
        if not self._lib_safe:
            raise MinitrinoError("lib_dir accessed before initialization")
        if not self._lib_dir:
            self._lib_dir = self._get_lib_dir()
        return self._lib_dir

    def _get_lib_dir(self) -> str:
        """Determine and validate the path to the library directory.

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
        with contextlib.suppress(Exception):
            lib_dir = self.env.get("LIB_PATH", "")

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
        """Create the `~/.minitrino` directory if not exists.

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
                ) from e
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
        """Return the path to the user's `minitrino.cfg` file.

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
            lib_env = self.env._parse_library_env()
            # Also check for port variables in OS environment
            for k, _v in lib_env.items():
                if k.startswith("__PORT"):
                    # Check if this port var exists in OS env and isn't already set
                    os_val = os.environ.get(k)
                    if os_val and not self.env.get(k):
                        self.env[k] = str(os_val)
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
        """Set cluster-related attributes for the context.

        Parameters
        ----------
        cluster_name : str
            The name of the cluster to set.
        """
        self.cluster = Cluster(self)
        self._set_cluster_name(cluster_name)
        self.env.update(
            {
                "COMPOSE_PROJECT_NAME": self.cluster.resource.compose_project_name(
                    self.cluster_name
                )
            }
        )

    def _set_cluster_name(self, cluster_name: str) -> None:
        """Determine and validate the active cluster name.

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

        self.cluster.validator.check_cluster_name()

        if self.cluster_name == "all":
            self.all_clusters = True

        self.env.update({"CLUSTER_NAME": self.cluster_name})
        self.logger.debug(f"Cluster name set to: {self.cluster_name}")

    def _set_docker_clients(self, env: dict | None = None) -> None:
        """Initialize Docker clients.

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
