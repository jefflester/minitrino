#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import click
import docker
import subprocess

from minipresto.cli import pass_environment

from minipresto.settings import RESOURCE_LABEL
from minipresto.settings import MODULE_LABEL_KEY_ROOT
from minipresto.settings import MODULE_ROOT


class CommandExecutor(object):
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
        - `handle_error`: If `False`, errors (non-zero return codes) are not
          handled by the function.
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

        cmd_details = []
        if kwargs.get("container", None):
            for command in kwargs.get("commands", []):
                cmd_details = self._execute_in_container(command, **kwargs)
        else:
            for command in kwargs.get("commands", []):
                cmd_details = self._execute_in_shell(command, **kwargs)
        return cmd_details

    def _execute_in_shell(self, command="", **kwargs):
        """
        Executes a command in the shell.
        """

        self.ctx.vlog(f"Preparing to execute command in shell:\n{command}")

        cmd_details = []
        process = subprocess.Popen(
            command,
            shell=True,
            env=kwargs.get("environment", {}),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        if not kwargs.get("suppress_output", False):
            while True:  # Stream output
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    output = self._strip_ansi(str(output))
                    self.ctx.vlog(output.strip())
        output, _ = process.communicate()
        if process.returncode != 0 and kwargs.get("handle_error", True):
            self.ctx.log_err(
                f"Failed to execute shell command:\n{command}\n"
                f"Exit code: {process.returncode}"
            )
            sys.exit(1)

        cmd_details.append(
            {
                "command": command,
                "output": self._strip_ansi(str(output)),
                "return_code": process.returncode,
            }
        )
        return cmd_details

    def _execute_in_container(self, command="", **kwargs):
        """
        Executes a command inside of a container through the Docker SDK (similar
        to docker exec).
        """

        container = kwargs.get("container", None)
        self.ctx.vlog(
            f"Preparing to execute command in container '{container.name}':\n{command}"
        )

        cmd_details = []
        exec_handler = self.ctx.api_client.exec_create(
            container.name,
            cmd=command,
            privileged=True,
            user=kwargs.get("docker_user", "root"),
        )

        # Executes the command and returns a binary output generator
        output = self.ctx.api_client.exec_start(exec_handler, stream=True)
        output_string = ""

        for line in output:
            # Stream generator output & decode binary to string
            line = self._strip_ansi(line.decode().strip())
            output_string += line
            if not kwargs.get("suppress_output", False):
                self.ctx.vlog(line)
        return_code = self.ctx.api_client.exec_inspect(exec_handler["Id"]).get(
            "ExitCode"
        )
        if return_code != 0 and kwargs.get("handle_error", True):
            self.ctx.log_err(
                f"Failed to execute command in container '{container.name}':\n{command}\n"
                f"Exit code: {return_code}"
            )
            sys.exit(1)

        cmd_details.append(
            {"command": command, "output": output_string, "return_code": return_code}
        )
        return cmd_details

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


class ComposeEnvironment(object):
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

        self.compose_env_string, self.compose_env_dict = self._get_compose_env(ctx, env)

    def _get_compose_env(self, ctx, env=[]):
        """
        Merges environment variables from library's root `.env` file, the
        Minipresto configuration file, and variables provided via the `--env`
        flag. Values from `--env` will override variables from everything else.
        Returns a shell-compatible string of key-value pairs and a dict.
        """

        env_file = os.path.join(ctx.minipresto_lib_dir, ".env")
        if not os.path.isfile(env_file):
            ctx.log_err(f"Environment file does not exist at path: {env_file}")
            sys.exit(1)

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
            ctx.log_err(f"Environment file not loaded properly from path: {env_file}")
            sys.exit(1)

        config = ctx.get_config(False)
        try:
            config_dict = dict(config.items("MODULES"))
        except:
            ctx.log_warn(
                f"No MODULES section found in {ctx.config_file}\n"
                f"To pass environment variables to Minipresto containers, you will need to populate this section."
            )
            config_dict = {}

        # Merge environment file config with Minipresto config
        config_dict.update(env_file_dict)

        # Add env variables and override existing if necessary
        if env:
            for env_variable in env:
                env_variable_list = env_variable.split("=")
                if not len(env_variable_list) == 2:
                    ctx.log_err(
                        f"Invalid environment variable: '{env_variable}'. Should be formatted as KEY=VALUE."
                    )
                    sys.exit(1)
                try:
                    del config_dict[env_variable_list[0].strip()]  # remove if present
                except:
                    pass
                config_dict[env_variable_list[0].strip()] = env_variable_list[1].strip()

        environment_formatted = ""
        for key, value in config_dict.items():
            environment_formatted += f"{key}: {value}\n"
        ctx.vlog(f"Registered environment variables:\n{environment_formatted}")

        return self._get_env_string(config_dict), config_dict

    def _get_env_string(self, compose_env_dict={}):
        """Returns a string of key-value pairs from a dict."""

        compose_env_list = []
        for key, value in compose_env_dict.items():
            compose_env_list.append(f'{key}="{value}" ')
        return "".join(compose_env_list)


class Modules(object):
    def __init__(self, ctx):
        """
        Contains information about running Minipresto modules. If no Minipresto
        containers are running, all properties will be equal to None or an empty
        type, such as `[]`.

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
        catalog, security = self._parse_module_label_values(module_label_vals)

        return containers, module_label_vals, catalog, security

    def _get_running_containers(self):
        """Gets all running minipresto containers."""

        containers = self.ctx.docker_client.containers.list(
            filters={"label": RESOURCE_LABEL}
        )
        return containers

    def _get_module_label_values(self, containers=[]):
        """Gets all module label values from list of containers."""

        if not containers:
            return None

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
            return None, None

        catalog = []
        security = []

        for value in module_label_vals:
            if "catalog-" in value:
                catalog.append(value.strip().replace("catalog-", ""))
            elif "security-" in value:
                security.append(value.strip().replace("security-", ""))
            else:
                self.ctx.log_err(f"Invalid module label value '{value}'.")
                sys.exit(1)
        return catalog, security


@pass_environment
def check_daemon(ctx):
    """Checks if the Docker daemon is running."""

    try:
        ctx.docker_client.ping()
    except:
        ctx.log_err(
            f"Error when pinging the Docker server. Is the Docker daemon running?"
        )
        sys.exit(1)


@pass_environment
def validate_module_dirs(ctx, module_type="", modules=[]):
    """
    Validates that the directory and Docker Compose .yml exist for each provided
    module. After validation, a list of module directories and YAML file paths
    is returned.

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
            ctx.log_err(f"Invalid {module_type} module: '{module}'.")
            sys.exit(1)
        module_dirs.append(module_dir)
        module_yaml_files.append(yaml_path)

    return module_dirs, module_yaml_files


def validate_yes_response(response=""):
    """Validates 'yes' user input."""

    response = response.replace(" ", "")
    if response.lower() == "y" or response.lower() == "yes":
        return True
    return False
