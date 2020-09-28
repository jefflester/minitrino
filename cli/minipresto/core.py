#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import click
import docker
import traceback
import subprocess

from minipresto.cli import pass_environment
from minipresto.cli import LogLevel
from minipresto.exceptions import MiniprestoException

from minipresto.settings import RESOURCE_LABEL
from minipresto.settings import MODULE_LABEL_KEY_ROOT
from minipresto.settings import MODULE_ROOT


class CommandExecutor:
    def __init__(self, ctx=None):
        """
        Executes commands in the host shell with customized handling of
        stdout/stderr output.

        Methods
        -------
        - `execute_commands()`: Executes commands in the user's shell or inside
          of a container.
        """

        self.ctx = ctx

    def execute_commands(self, **kwargs):
        """
        Executes commands in the user's shell or inside of a container.

        Parameters
        ----------
        - `trigger_error`: If `False`, errors (non-zero exit codes) from
          commands will not raise an exception. Defaults to `False`.
        - `environment`: A dictionary of environment variables to pass to the
          subprocess.
        - `commands`: A list of commands that will be executed in the order
          provided.
        - `suppress_output`: If `True`, output from the executed command will be
          suppressed.
        - `container`: A Docker container object. If passed in, the command will
          be executed through the Docker SDK instead of the subprocess module.
        - `docker_user`: The user to execute the command as in the Docker
          container (default: `root`).

        Return Values
        -------------
        - A list of dicts with each dict containing the following keys:
            - `command`: the original command passed to the function
            - `output`: the combined output of stdout and stderr
            - `return_code`: the return code of the command
        """

        kwargs["environment"] = self._construct_environment(
            kwargs.get("environment", {})
        )

        try:
            cmd_details = []
            if kwargs.get("container", None):
                for command in kwargs.get("commands", []):
                    cmd_details.append(self._execute_in_container(command, **kwargs))
            else:
                for command in kwargs.get("commands", []):
                    cmd_details.append(self._execute_in_shell(command, **kwargs))
            return cmd_details
        except MiniprestoException as e:
            handle_exception(e)

    def _execute_in_shell(self, command="", **kwargs):
        """
        Executes a command in the shell.
        """

        self.ctx.log(
            f"Preparing to execute command in shell:\n{command}",
            level=LogLevel().verbose,
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
            while True:
                output_line = process.stdout.readline()
                if output_line == "" and process.poll() is not None:
                    break
                output_line = self._strip_ansi(output_line)
                self.ctx.log(output_line, level=LogLevel().verbose)

        output, _ = process.communicate()  # Get full output (stdout + stderr)
        if process.returncode != 0 and kwargs.get("trigger_error", False):
            raise MiniprestoException(
                f"Failed to execute shell command:\n{command}\n"
                f"Exit code: {process.returncode}"
            )

        return {
            "command": command,
            "output": self._strip_ansi(output),
            "return_code": process.returncode,
        }

    def _execute_in_container(self, command="", **kwargs):
        """
        Executes a command inside of a container through the Docker SDK (similar
        to docker exec).
        """

        container = kwargs.get("container", None)
        if container is None:
            raise MiniprestoException(
                "Attempted to execute a command inside of a container, but a container object was not provided."
            )

        self.ctx.log(
            f"Preparing to execute command in container '{container.name}':\n{command}",
            level=LogLevel().verbose,
        )

        # Create exec handler and execute the command
        exec_handler = self.ctx.api_client.exec_create(
            container.name,
            cmd=command,
            privileged=True,
            user=kwargs.get("docker_user", "root"),
        )

        # `output` is a generator yielding response chunks
        output_generator = self.ctx.api_client.exec_start(exec_handler, stream=True)

        # Output from generator is returned as bytes, so they need to be decoded
        # to strings. Additionally, the output is not guaranteed a full line,
        # but is instead chunks of lines. A newline in the output chunk will
        # trigger a log dump up to the first newline in the given chunk. The
        # remainder of the chunk (if any) is stored in `full_line`.
        output = ""
        full_line = ""
        for chunk in output_generator:
            chunk = self._strip_ansi(chunk.decode())
            output += chunk
            chunk = chunk.split("\n", 1)
            if len(chunk) > 1:  # Indicates newline present
                full_line += chunk[0]
                if not kwargs.get("suppress_output", False):
                    self.ctx.log(full_line, level=LogLevel().verbose)
                    full_line = ""
                if chunk[1]:
                    full_line = chunk[1]
            else:
                full_line += chunk[0]

        # Catch lingering full line post-loop
        if not kwargs.get("suppress_output", False) and full_line:
            self.ctx.log(full_line, level=LogLevel().verbose)

        return_code = self.ctx.api_client.exec_inspect(exec_handler["Id"]).get(
            "ExitCode"
        )

        if return_code != 0 and kwargs.get("trigger_error", False):
            raise MiniprestoException(
                f"Failed to execute command in container '{container.name}':\n{command}\n"
                f"Exit code: {return_code}"
            )

        return {"command": command, "output": output, "return_code": return_code}

    def _construct_environment(self, environment={}):
        """
        Merges provided environment dictionary with user's shell environment
        variables.
        """

        # Remove conflicting keys from host environment; user config and Compose
        # config take precendance
        host_environment = os.environ.copy()
        if environment:
            delete = []
            for host_key, host_value in host_environment.items():
                for key, value in environment.items():
                    if key == host_key:
                        delete.append(host_key)
            for delete_key in delete:
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


class ComposeEnvironment:
    def __init__(self, ctx=None, env=[]):
        """
        Creates a string and a dictionary of environment variables for use by
        Docker Compose. Environment variables are sourced from the user's
        `minipresto.cfg` file and the `.env` file in the Minipresto library.
        These two resources are parsed and combined into a single environment
        dictionary.

        Parameters
        ----------
        - `ctx`: environment object (minipresto.cli.Environment).
        - `env`: A list of `key=value` environment variables to append to the
          environment variable dictionary.

        Properties
        ----------
        - `compose_env_string`: String of environment variables in `key=value`
          format delimited by spaces.
        - `compose_env_dict`: Dictionary of environment variables.
        """

        try:
            self.compose_env_string, self.compose_env_dict = self._get_compose_env(
                ctx, env
            )
            self._log_environment_variables(ctx, self.compose_env_dict)
        except MiniprestoException as e:
            handle_exception(e)

    def _get_compose_env(self, ctx, env=[]):
        """
        Merges environment variables from library's root `.env` file, the
        Minipresto configuration file, and variables provided via the `--env`
        flag. Values from `--env` will override variables from everything else.
        Returns a shell-compatible string of key-value pairs and a dict.
        """

        compose_env_dict = {}

        env_file = os.path.join(ctx.minipresto_lib_dir, ".env")
        if not os.path.isfile(env_file):
            raise MiniprestoException(
                f"Environment file does not exist at path: {env_file}"
            )

        env_file_dict = {}
        with open(env_file, "r") as f:
            for env_variable in f:
                env_variable = env_variable.strip()
                if not env_variable:
                    continue
                env_variable = env_variable.split("=")
                if len(env_variable) == 2:
                    env_file_dict[env_variable[0].strip()] = env_variable[1].strip()

        if not env_file_dict:
            raise MiniprestoException(
                f"Environment file not loaded properly from path: {env_file}"
            )

        compose_env_dict.update(env_file_dict)

        config = ctx.get_config()
        try:
            user_config_dict = dict(config.items("MODULES"))
        except:
            ctx.log(
                f"No 'MODULES' section found in {ctx.config_file}\n"
                f"To pass environment variables to Minipresto containers, you will need to populate this section.",
                level=LogLevel().warn,
            )
            user_config_dict = {}

        # Merge environment file config with Minipresto config
        compose_env_dict.update(user_config_dict)

        # Add env variables and override existing if necessary
        if env:
            for env_variable in env:
                env_variable_list = env_variable.split("=")
                if not len(env_variable_list) == 2:
                    raise MiniprestoException(
                        f"Invalid environment variable: '{env_variable}'. Should be formatted as KEY=VALUE."
                    )
                try:
                    del compose_env_dict[
                        env_variable_list[0].strip()
                    ]  # remove if present
                except:
                    pass
                compose_env_dict[env_variable_list[0].strip()] = env_variable_list[
                    1
                ].strip()

        return self._get_env_string(compose_env_dict), compose_env_dict

    def _get_env_string(self, compose_env_dict={}):
        """Returns a string of key-value pairs from a dict."""

        compose_env_list = []
        for key, value in compose_env_dict.items():
            compose_env_list.append(f'{key}="{value}" ')
        return "".join(compose_env_list)

    def _log_environment_variables(self, ctx, compose_env_dict):
        """Logs environment variables."""

        longest_key = 0
        for key, value in compose_env_dict.items():
            if not longest_key:
                longest_key = len(key)
            elif len(key) > longest_key:
                longest_key = len(key)

        environment_formatted = ""
        for key, value in compose_env_dict.items():
            environment_formatted += (
                f"{key}{' ' * (longest_key + 4 - len(key))}{value}\n"
            )
        ctx.log(
            f"Registered environment variables:\n{environment_formatted}",
            level=LogLevel().verbose,
        )


class Modules:
    def __init__(self, ctx):
        """
        Contains information about running Minipresto modules. If no Minipresto
        containers are running, all properties will be equal to an empty type,
        such as `[]`.

        Parameters
        ----------
        - `ctx: minipresto.cli.Environment`: client environment object.

        Properties
        ----------
        - `containers: []`: List of Docker container objects that map to active
          Minipresto modules.
        - `module_label_vals: []`: List of labels tied to active Minipresto
          containers. Presto container is excluded from the list.
        - `catalog: []`: List of active catalog module names.
        - `security []`: List of active security module names.
        """

        self.ctx = ctx
        (
            self.containers,
            self.module_label_vals,
            self.catalog,
            self.security,
        ) = self._get_running_modules()

    def _get_running_modules(self):
        """Returns list of running modules."""

        check_daemon()
        containers = self._get_running_containers()
        module_label_vals = self._get_module_label_values(containers)
        try:
            catalog, security = self._parse_module_label_values(module_label_vals)
        except MiniprestoException as e:
            handle_exception(e)

        return containers, module_label_vals, catalog, security

    def _get_running_containers(self):
        """Gets all running Minipresto containers."""

        containers = self.ctx.docker_client.containers.list(
            filters={"label": RESOURCE_LABEL}
        )
        return containers

    def _get_module_label_values(self, containers=[]):
        """Gets all module label values from list of containers."""

        if not containers:
            return []

        module_label_vals = []
        for container in containers:
            for key, value in container.labels.items():
                if MODULE_LABEL_KEY_ROOT in key:
                    if value not in module_label_vals:
                        module_label_vals.append(value)

        # Presto is unneeded, as the service is defined in docker-compose.yml and
        # that is copied over by default
        module_label_vals.remove("presto")
        return module_label_vals

    def _parse_module_label_values(self, module_label_vals=[]):
        """
        Parses module label values and returns a tuple of lists used to identify
        the correct directories to copy into the named snapshot directory.
        """

        if not module_label_vals:
            return [], []

        catalog = []
        security = []

        for value in module_label_vals:
            if "catalog-" in value:
                catalog.append(value.strip().replace("catalog-", ""))
            elif "security-" in value:
                security.append(value.strip().replace("security-", ""))
            else:
                raise MiniprestoException(f"Invalid module label value '{value}'.")
        return catalog, security


@pass_environment
def handle_exception(ctx, e=MiniprestoException, log_msg=True, sys_exit=True):
    """
    Gracefully handles MiniprestoException exceptions.

    Parameters
    ----------
    - `e`: The MiniprestoException object.
    - `log_msg`: if `True`, the exception message will be logged through
      Minipresto's error logging function.
    - `sys_exit`: If `True`, Minipresto will exit with the exception's exit code.
    """

    if not isinstance(e, MiniprestoException):
        raise Exception(
            "Incorrect object type for parameter 'e'. Expected: MiniprestoException"
        )

    if log_msg:
        ctx.log(e.msg, level=LogLevel().error)

    if ctx.verbose:
        click.echo(f"\n{traceback.format_exc()}", err=True)

    if sys_exit:
        sys.exit(e.exit_code)


@pass_environment
def handle_generic_exception(ctx, e=Exception, log_msg=True, sys_exit=True):
    """
    Gracefully handles generic exceptions. Prints a stacktrace if verbose mode
    is enabled.

    Parameters
    ----------
    - `e`: The Exception object.
    - `log_msg`: if `True`, the exception message will be logged through
      Minipresto's error logging function.
    - `sys_exit`: If `True`, Minipresto will exit with the exception's exit
      code.
    """

    if not isinstance(e, Exception):
        raise Exception("Incorrect object type for parameter 'e'. Expected: Exception")

    if log_msg:
        ctx.log(str(e), level=LogLevel().error)

    if ctx.verbose:
        click.echo(f"\n{traceback.format_exc()}", err=True)

    if sys_exit:
        sys.exit(1)


@pass_environment
def check_daemon(ctx):
    """
    Checks if the Docker daemon is running. Raises and handles a
    MiniprestoException if not.
    """

    def ping():
        try:
            ctx.docker_client.ping()
        except:
            raise MiniprestoException(
                f"Error when pinging the Docker server. Is the Docker daemon running?"
            )

    try:
        ping()
    except MiniprestoException as e:
        handle_exception(e)


@pass_environment
def validate_module_dirs(ctx, module_type="", modules=[]):
    """
    Validates that the directory and Docker Compose .yml exist for each provided
    module. After validation, a list of module directories and YAML file paths
    is returned.

    Raises a MiniprestoException if the module does not exist.

    Parameters
    ----------
    - `module_type`: one of minipresto.settings.MODULE_CATALOG or
      minipresto.settings.MODULE_SECURITY.
    - `modules`: a list of module root names.
    """

    module_dirs = []
    module_yaml_files = []

    for module in modules:
        module_dir = os.path.abspath(
            os.path.join(ctx.minipresto_lib_dir, MODULE_ROOT, module_type, module)
        )
        yaml_path = os.path.join(module_dir, f"{module}.yml")

        if not (os.path.isfile(yaml_path)):
            raise MiniprestoException(f"Invalid {module_type} module: '{module}'.")
        module_dirs.append(module_dir)
        module_yaml_files.append(yaml_path)

    return module_dirs, module_yaml_files


def generate_identifier(identifiers=None):
    """
    Returns an 'object identifier' string used for creating log messages, e.g.
    '[ID: 12345] [Name: presto]'.

    Parameters
    ----------
    - `identifiers`: Dictionary of "identifier_value": "identifier_key" pairs.
    """

    if not identifiers:
        raise MiniprestoException(
            "Identifiers are required to generate an object identifier."
        )

    object_identifier = []
    for key, value in identifiers.items():
        object_identifier.append(f"[{key}: {value}]")
    return " ".join(object_identifier)


def validate_yes_response(response=""):
    """Validates 'yes' user input."""

    response = response.replace(" ", "")
    if response.lower() == "y" or response.lower() == "yes":
        return True
    return False
