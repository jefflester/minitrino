#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import json
import re
import yaml
import docker
import subprocess

from pathlib import Path
from configparser import ConfigParser

from minitrino import utils
from minitrino import errors as err
from minitrino.settings import RESOURCE_LABEL
from minitrino.settings import MODULE_ROOT
from minitrino.settings import MODULE_ADMIN
from minitrino.settings import MODULE_SECURITY
from minitrino.settings import MODULE_CATALOG
from minitrino.settings import CONFIG_TEMPLATE


class Environment:
    """Provides context and core controls that are globally accessible in
    command scripts. This class should not be instantiated from anywhere but the
    CLI's entrypoint, as it depends on user-provided inputs.

    ### Public Attributes (Interactive)

    - `logger`: A `minitrino.utils.Logger` object.
    - `env`: An `EnvironmentVariables` object containing all CLI environment
        variables, subdivided by sections when possible.
    - `modules`: A `Modules` object containing metadata about Minitrino modules.
    - `cmd_executor`: A `CommandExecutor` object to execute shell commands in
      the host shell and inside containers.
    - `docker_client`: A `docker.DockerClient` object.
    - `api_client`: A `docker.APIClient` object.

    ### Public Attributes (Static)

    - `verbose`: If `True`, logs flagged as verbose to are sent to stdout.
    - `user_home_dir`: The home directory of the current user.
    - `minitrino_user_dir`: The location of the Minitrino directory relative to
      the user home directory (~/.minitrino/).
    - `config_file`: The location of the user's minitrino.cfg file.
    - `snapshot_dir`: The location of the user's snapshot directory (this is
        essentially a temporary directory, as 'permanent' snapshot tarballs are
        written to the library or user-specified directory).
    - `minitrino_lib_dir`: The location of the Minitrino library."""

    @utils.exception_handler
    def __init__(self):
        # Attributes that depend on user input prior to being set
        self.verbose = False
        self._user_env = []

        self.logger = utils.Logger()
        self.env = EnvironmentVariables
        self.modules = Modules
        self.cmd_executor = CommandExecutor
        self.docker_client = docker.DockerClient
        self.api_client = docker.APIClient

        # Paths
        self.user_home_dir = os.path.expanduser("~")
        self.minitrino_user_dir = self._handle_minitrino_user_dir()
        self.config_file = self._get_config_file()
        self.snapshot_dir = os.path.join(self.minitrino_user_dir, "snapshots")
        self._minitrino_lib_dir = None

    @property
    def minitrino_lib_dir(self):
        if not self._minitrino_lib_dir:
            self._minitrino_lib_dir = self._get_minitrino_lib_dir()
        return self._minitrino_lib_dir

    def _get_minitrino_lib_dir(self):
        """Gets the library directory. The directory can be determined in the
        following order of precedence:

        1. Pass `LIB_PATH` via env (`--env` option, OS env, or Minitrino config
           file)
        2. Check to see if the library exists in relation to the positioning of
           the `components.py`file and assume the project is running in a
           repository."""

        lib_dir = ""
        try:
            lib_dir = self.env.get("LIB_PATH", "")
        except:
            pass

        if not lib_dir and os.path.isdir(os.path.join(self.minitrino_user_dir, "lib")):
            lib_dir = os.path.join(self.minitrino_user_dir, "lib")
        elif not lib_dir:  # Use repo root, fail if this doesn't exist
            lib_dir = Path(os.path.abspath(__file__)).resolve().parents[2]
            lib_dir = os.path.join(lib_dir, "lib")

        if not os.path.isdir(lib_dir) or not os.path.isfile(
            os.path.join(lib_dir, "minitrino.env")
        ):
            raise err.UserError(
                "This operation requires a library to be installed.",
                f"The library can be installed in the default location (~/.minitrino/lib) "
                f"via the `lib-install` command, or it can be pointed to with the `LIB_PATH` "
                f"environment variable.",
            )

        self.logger.verbose(
            f"Library path set to: {lib_dir}",
        )
        return lib_dir

    @utils.exception_handler
    def _user_init(self, verbose=False, user_env=[]):
        """Initialize attributes that depend on user-provided input."""

        # Set attributes
        self.verbose = verbose
        self._user_env = user_env
        self.logger = utils.Logger(self.verbose)
        self.env = EnvironmentVariables(self)

        try:
            # Attempt to parse lib env file & fetch modules
            self.env._parse_library_env()
            self.modules = Modules(self)

            cli_ver = utils.get_cli_ver()
            lib_ver = utils.get_lib_ver(self.minitrino_lib_dir)
            if cli_ver != lib_ver:
                self.logger.warn(
                    f"CLI version {cli_ver} and library version {lib_ver} "
                    f"do not match. You can update the Minitrino library "
                    f"version to match the CLI version by running 'minitrino "
                    f"lib-install'.",
                )
        except:  # Skip lib-related procedures if the lib is not found
            pass

        self.env._log_env_vars()
        self.cmd_executor = CommandExecutor(self)
        self._get_docker_clients()

    def _handle_minitrino_user_dir(self):
        """Checks if a Minitrino directory exists in the user home directory.
        If not, it is created. The path to the Minitrino user home directory is
        returned."""

        minitrino_user_dir = os.path.abspath(
            os.path.join(self.user_home_dir, ".minitrino")
        )
        if not os.path.isdir(minitrino_user_dir):
            os.mkdir(minitrino_user_dir)
        return minitrino_user_dir

    def _get_config_file(self):
        """Returns the file path of the minitrino.cfg file. Warns if the file
        path regardless for future creation."""

        config_file = os.path.join(self.minitrino_user_dir, "minitrino.cfg")
        if not os.path.isfile(config_file):
            self.logger.warn(
                f"No minitrino.cfg file found at {config_file}. "
                f"Run 'minitrino config' to reconfigure this file and directory.",
            )
        return config_file

    def _get_docker_clients(self):
        """Gets DockerClient and APIClient objects. Returns a tuple of DockerClient
        and APIClient objects, respectively. Returns None types for each client
        if they fail to fetch."""

        self.logger.verbose(
            "Attempting to locate Docker socket file for current Docker context..."
        )

        try:
            output = self.cmd_executor.execute_commands(
                "docker context inspect", suppress_output=True
            )
            context = json.loads(output[0].get("output", ""))[0]
            socket = context["Endpoints"]["docker"].get("Host", "")
        except Exception as e:
            raise err.MinitrinoError(
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
            return None, None


class EnvironmentVariables(dict):
    """Exposes all Minitrino variables.

    ### Parameters

    - `ctx`: Instantiated Environment object (with user input already accounted
      for).

    ### Usage

    ```python # ctx object has an instantiated EnvironmentVariables object
    env_variable = ctx.env.get("STARBURST_VER", "388-e")
    ```"""

    @utils.exception_handler
    def __init__(self, ctx=None):
        super().__init__()

        self._ctx = ctx
        self._parse_user_env()
        self._parse_os_env()
        self._parse_minitrino_config()

    def _parse_user_env(self):
        """Parses user-provided environment variables for the current
        command."""

        if not self._ctx._user_env:
            return

        for env_var in self._ctx._user_env:
            env_var = utils.parse_key_value_pair(env_var, err_type=err.UserError)
            self[env_var[0]] = env_var[1]

    def _parse_os_env(self):
        """Parses environment variables from the user's shell."""

        append = ["LIB_PATH", "STARBURST_VER", "TEXT_EDITOR", "LIC_PATH"]
        for k, v in os.environ.items():
            k = k.upper()
            if k in append and not self.get(k, None):
                self[k] = v

    def _parse_minitrino_config(self):
        """Parses the Minitrino config file and adds it to the env
        dictionary."""

        if not os.path.isfile(self._ctx.config_file):
            return

        try:
            config = ConfigParser()
            config.optionxform = str  # Preserve case
            config.read(self._ctx.config_file)
            for k, v in config.items("config"):
                if not self.get(k, None) and v:
                    self[k.upper()] = v
        except Exception as e:
            self._ctx.logger.warn(
                f"Failed to parse config file {self._ctx.config_file} with error:\n{str(e)}\n"
                f"Variables set in the config file will not be loaded. "
                f"You can reset your configuration file with `minitrino config --reset` or "
                f"edit it manually with `minitrino config`. The valid config file structure is: \n"
                f"{CONFIG_TEMPLATE}"
            )
            return

    def _parse_library_env(self):
        """Parses the Minitrino library's `minitrino.env` file. Lowest
        precedence in environment variable order, loaded during
        `_user_init()`."""

        env_file = os.path.join(self._ctx.minitrino_lib_dir, "minitrino.env")
        if not os.path.isfile(env_file):
            raise err.UserError(
                f"Library 'minitrino.env' file does not exist at path: {env_file}",
                f"Are you pointing to a valid library, and is the minitrino.env file "
                f"present in that library?",
            )

        with open(env_file, "r") as f:
            for env_var in f:
                env_var = utils.parse_key_value_pair(env_var, err_type=err.UserError)
                if env_var is None:
                    continue
                if not self.get(env_var[0], None):
                    self[env_var[0]] = env_var[1]

    def _log_env_vars(self):
        """Logs environment variables."""

        if self:
            self._ctx.logger.verbose(
                f"Registered environment variables:\n{json.dumps(self, indent=2)}",
            )


class Modules:
    """Contains information about all valid Minitrino modules.

    ### Parameters
    - `ctx`: Instantiated Environment object (with user input already accounted
      for).

    ### Public Attributes
    - `data`: A dictionary of module information.

    ### Public Methods
    - `get_running_modules()`: Returns a list of running modules."""

    @utils.exception_handler
    def __init__(self, ctx=None):
        self.data = {}
        self._ctx = ctx
        self._load_modules()

    def get_running_modules(self):
        """Returns dict of running modules (includes container objects and
        Docker labels)."""

        utils.check_daemon(self._ctx.docker_client)
        containers = self._ctx.docker_client.containers.list(
            filters={"label": RESOURCE_LABEL}
        )

        if not containers:
            return []

        modules = []
        for container in containers:
            label_set = {}
            ids = ["admin-", "catalog-", "security-"]
            for k, v in container.labels.items():
                for _id in ids:
                    if "com.starburst.tests" in k and _id in v:
                        modules.append(v.lower().strip().replace(_id, ""))
                        label_set[k] = v
            # All containers except the trino containers must have
            # module-specific labels. The trino container only has module labels
            # if a module applies labels to it
            if not label_set and not (
                "trino-worker" in container.name or container.name == "trino"
            ):
                raise err.UserError(
                    f"Missing Minitrino labels for container '{container.name}'.",
                    f"Check this module's 'docker-compose.yml' file and ensure you are "
                    f"following the documentation on labels.",
                )

        modules = list(set(modules))
        for module in modules:
            if not isinstance(self.data.get(module), dict):
                raise err.UserError(
                    f"Module '{module}' is running, but it is not found "
                    f"in the library. Was it deleted, or are you pointing "
                    f"Minitrino to the wrong location?"
                )
        return modules

    def _load_modules(self):
        """Loads module data during instantiation."""

        self._ctx.logger.verbose("Loading modules...")

        modules_dir = os.path.join(self._ctx.minitrino_lib_dir, MODULE_ROOT)
        if not os.path.isdir(modules_dir):
            raise err.MinitrinoError(
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

                yaml_basename = f"{os.path.basename(module_dir)}.yml"
                if not yaml_basename in module_files:
                    raise err.UserError(
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


class CommandExecutor:
    """Executes commands in the host shell/host containers with customized
    handling of stdout/stderr output.

    ### Parameters

    - `ctx`: Instantiated Environment object (with user input already accounted
      for).

    ### Public Methods

    - `execute_commands()`: Executes commands in the user's shell or inside of a
        container."""

    @utils.exception_handler
    def __init__(self, ctx=None):
        self._ctx = ctx

    def execute_commands(self, *args, **kwargs):
        """Executes commands in the user's shell or inside of a container.
        Returns output as well as stores the output in the `output` attribute.

        ### Parameters

        - `args`: Commands that will be executed in the order provided.

        Keyword Arguments:

        - `trigger_error`: If `False`, errors (non-zero exit codes) from
          executed commands will not raise an exception. Defaults to `True`.
        - `environment`: A dictionary of environment variables to pass to the
          subprocess or container.
        - `suppress_output`: If `True`, output to stdout from the executed
          command will be suppressed.
        - `container`: A Docker container object. If passed in, the command will
          be executed through the Docker SDK instead of the subprocess module.
        - `docker_user`: The user to execute the command as in the Docker
          container (default: `root`).

        ### Return Values

        - A list of dicts with each dict containing the following keys:
            - `command`: the original command passed to the function
            - `output`: the combined output of stdout and stderr
            - `return_code`: the return code of the command"""

        output = []
        if kwargs.get("container", None):
            kwargs["environment"] = self._construct_environment(
                kwargs.get("environment", {}), kwargs.get("container", None)
            )
            for command in args:
                output.append(self._execute_in_container(command, **kwargs))
        else:
            kwargs["environment"] = self._construct_environment(
                kwargs.get("environment", {})
            )
            for command in args:
                output.append(self._execute_in_shell(command, **kwargs))

        return output

    def _execute_in_shell(self, command="", **kwargs):
        """Executes a command in the host shell."""

        self._ctx.logger.verbose(
            f"Executing command in shell:\n{command}",
        )

        process = subprocess.Popen(
            command,
            shell=True,
            env=kwargs.get("environment", {}),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        if not kwargs.get("suppress_output", False):
            # Stream the output of the executed command line-by-line.
            # `universal_newlines=True` ensures output is generated as a string,
            # so there is no need to decode bytes. The only cleansing we need to
            # do is to run the string through the `_strip_ansi()` function.

            started_stream = False
            output = ""
            while True:
                output_line = process.stdout.readline()
                if output_line == "" and process.poll() is not None:
                    break
                output_line = self._strip_ansi(output_line)
                if not started_stream:
                    self._ctx.logger.verbose("Command Output:")
                    started_stream = True
                self._ctx.logger.verbose(output_line, stream=True)
                output += output_line
        else:
            output, _ = process.communicate()

        if process.returncode != 0 and kwargs.get("trigger_error", True):
            raise err.MinitrinoError(
                f"Failed to execute shell command:\n{command}\n"
                f"Exit code: {process.returncode}"
            )

        return {
            "command": command,
            "output": self._strip_ansi(output),
            "return_code": process.returncode,
        }

    def _execute_in_container(self, command="", **kwargs):
        """Executes a command inside of a container through the Docker SDK
        (similar to `docker exec`)."""

        container = kwargs.get("container", None)
        if container is None:
            raise err.MinitrinoError(
                f"Attempted to execute a command inside of a "
                f"container, but a container object was not provided."
            )

        if not kwargs.get("suppress_output"):
            self._ctx.logger.verbose(
                f"Executing command in container '{container.name}':\n{command}",
            )

        # Create exec handler and execute the command
        exec_handler = self._ctx.api_client.exec_create(
            container.name,
            cmd=command,
            environment=kwargs.get("environment", {}),
            privileged=True,
            user=kwargs.get("docker_user", "root"),
        )

        # `output` is a generator that yields response chunks
        output_generator = self._ctx.api_client.exec_start(exec_handler, stream=True)

        # Output from the generator is returned as bytes, so they need to be
        # decoded to strings. Response chunks are not guaranteed to be full
        # lines. A newline in the output chunk will trigger a log dump of the
        # current `full_line` up to the first newline in the current chunk. The
        # remainder of the chunk (if any) resets the `full_line` var, then log
        # dumped when the next newline is received.

        output = ""
        full_line = ""
        started_stream = False
        for chunk in output_generator:
            chunk = self._strip_ansi(chunk.decode())
            output += chunk
            chunk = chunk.split("\n", 1)
            if len(chunk) > 1:  # Indicates newline present
                full_line += chunk[0]
                if not kwargs.get("suppress_output", False):
                    if not started_stream:
                        self._ctx.logger.verbose("Command Output:")
                        started_stream = True
                    self._ctx.logger.verbose(full_line, stream=True)
                    full_line = ""
                if chunk[1]:
                    full_line = chunk[1]
            else:
                full_line += chunk[0]

        # Catch lingering full line post-loop
        if not kwargs.get("suppress_output", False) and full_line:
            self._ctx.logger.verbose(full_line, stream=True)

        # Get the exit code
        return_code = self._ctx.api_client.exec_inspect(exec_handler["Id"]).get(
            "ExitCode"
        )
        # https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html
        if return_code == 126:
            self._ctx.logger.warn(
                f"The command exited with a 126 code which typically means an "
                f"executable is not accessible or installed. Does this image have "
                f"all required dependencies installed?\nCommand: {command}",
            )

        if return_code != 0 and kwargs.get("trigger_error", True):
            raise err.MinitrinoError(
                f"Failed to execute command in container '{container.name}':\n{command}\n"
                f"Exit code: {return_code}"
            )

        return {"command": command, "output": output, "return_code": return_code}

    def _construct_environment(self, environment={}, container=None):
        """Merges provided environment dictionary with user's shell environment
        variables. For shell execution, the host environment will be set to the
        existing variables in the host environment. For container execution, the
        host environment will be set to the container's existing environment
        variables."""

        # Remove conflicting keys from host environment; Minitrino environment
        # variables take precendance

        if not container:
            host_environment = os.environ.copy()
        else:
            host_environment_list = self._ctx.api_client.inspect_container(
                container.id
            )["Config"]["Env"]
            host_environment = {}
            for env_var in host_environment_list:
                env_var = utils.parse_key_value_pair(env_var)
                host_environment[env_var[0]] = env_var[1]

        if environment:
            delete_keys = []
            for host_key, host_value in host_environment.items():
                for key, value in environment.items():
                    if key == host_key:
                        delete_keys.append(host_key)
            for delete_key in delete_keys:
                del host_environment[delete_key]

        # Merge environment argument with copy of existing environment
        environment.update(host_environment)
        return environment

    def _strip_ansi(self, value=""):
        """Strips ANSI escape sequences from strings."""

        # Strip ANSI codes before Click so that our logging helpers
        # know if it's an empty string or not.
        ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_regex.sub("", value)
