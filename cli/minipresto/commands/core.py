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


class MultiArgOption(click.Option):
    """
    Extends Click's `Option` class to allow for multiple arguments in a single
    option without specifying the option twice, as is otherwise required via
    Click's Multiple Options:
    https://click.palletsprojects.com/en/7.x/options/#multiple-options)

    Class Implementation:
    https://stackoverflow.com/questions/48391777/nargs-equivalent-for-options-in-click

    Returns a tuple after parsing the input data.
    """

    def __init__(self, *args, **kwargs):
        nargs = kwargs.pop("nargs", -1)
        assert nargs == -1, f"nargs, if set, must be -1 not {nargs}"
        super(MultiArgOption, self).__init__(*args, **kwargs)
        self._previous_parser_process = None
        self._eat_all_parser = None

    def add_to_parser(self, parser, ctx):
        def parser_process(value, state):
            # Method to hook to the parser.process
            done = False
            value = [value]
            # Grab everything up to the next option
            while state.rargs and not done:
                for prefix in self._eat_all_parser.prefixes:
                    if state.rargs[0].startswith(prefix):
                        done = True
                if not done:
                    value.append(state.rargs.pop(0).strip())
            value = tuple(value)

            # Call the actual process
            self._previous_parser_process(value, state)

        retval = super(MultiArgOption, self).add_to_parser(parser, ctx)
        for name in self.opts:
            our_parser = parser._long_opt.get(name) or parser._short_opt.get(name)
            if our_parser:
                self._eat_all_parser = our_parser
                self._previous_parser_process = our_parser.process
                our_parser.process = parser_process
                break
        return retval


class CommandExecutor(object):
    def __init__(self, ctx):
        """
        Executes commands in the host shell with customized handling of
        stdout/stderr output.
        """

        self.ctx = ctx

    def execute_commands(self, handle_error=True, environment={}, *args):
        """
        Executes commands in a subprocess and returns a list of dictionaries
        containing information about each command's execution.
        """

        environment = self.construct_environment(environment)

        retval = []
        for arg in args:
            self.ctx.vlog(f"Preparing to execute command:\n{arg}")

            process = subprocess.Popen(
                arg,
                shell=True,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )

            output_full = ""
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    output = self.strip_ansi(output)
                    self.ctx.vlog(output.strip())
                output_full += output

            retval.append(
                {
                    "command": arg,
                    "output": output_full,
                    "return_code": process.returncode,
                }
            )

            if process.returncode != 0:
                if handle_error:
                    self.ctx.log_err(f"Failed to execute command:\n{arg}")
                    sys.exit(1)
            return retval

    def construct_environment(self, environment={}):
        """Constructs dictionary of environment variables."""

        # Remove conflicting keys from host environment; user config and Compose
        # keys take precendance
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

    def strip_ansi(self, value=""):
        """Strips ANSI escape sequences from strings."""

        # Strip ANSI codes before Click so that our logging helpers
        # know if it's an empty string or not.
        ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_regex.sub("", value)


class ComposeEnvironment(object):
    def __init__(self, ctx, env_override=[]):
        """
        Creates a string and a dictionary of environment variables. Environment
        variables are sourced from the user's `minipresto.cfg` file and the
        `.env` file in the Minipresto library.
        """

        self.ctx = ctx
        self.env_override = env_override
        self.compose_env_string, self.compose_env_dict = self.get_compose_env(
            env_override
        )

    def get_compose_env(self, env_override=[]):
        """
        Loads environment variables from root .env file and user configuration,
        then merges the two sets of environment variables. Returns a string of
        key-value pairs and a dict.
        """

        env_file = os.path.join(self.ctx.minipresto_lib_dir, ".env")
        if not os.path.isfile(env_file):
            self.ctx.log_err(f"Environment file does not exist at path {env_file}")
            sys.exit(1)

        config = self.ctx.get_config()
        if config:
            config_env = dict(config.items("DOCKER"))
        else:
            config_env = {}

        core_env = {}
        with open(env_file, "r") as env_file:
            for env_variable in env_file:
                if env_variable == "\n":
                    continue
                env_variable = env_variable.replace("\n", "")
                if env_override:
                    env_variable = self.handle_override(env_variable, env_override)
                key, value = self.validate_env_variable(env_variable)
                core_env[key] = value
                self.ctx.vlog(f"Registered environment variable: {env_variable}")

        if not core_env:
            self.ctx.log_err(
                f"Environment file not loaded properly from path:\n{env_file}"
            )
            sys.exit(1)

        # Update core environment dict with config environment dict
        config_env.update(core_env)
        compose_env_dict = config_env
        return self.get_env_string(compose_env_dict), compose_env_dict

    def handle_override(self, env_variable="", env_override=[]):
        """
        Returns the overridden value if the key matches an existing key.
        Otherwise, returns an unmodified key-value pair. 
        """

        match, override = self.check_override_match(env_variable, env_override)

        if match:
            self.ctx.vlog(f"Overrode environment variable {env_variable} to {override}")
            return override
        else:
            return env_variable

    def check_override_match(self, env_variable="", env_override=[]):
        """Checks if the given environment variable key matches a key in env_override_list."""

        env_variable = env_variable.strip().split("=")

        for override in env_override:
            override_split = override.split("=")
            if override_split[0].strip() == env_variable[0].strip():
                return True, override
        return False, None

    def validate_env_variable(self, env_variable=""):
        """
        Validates that an environment variable is a proper key/value pair.
        If valid, returns the key/value pair as a tuple.
        """

        env_variable_list = env_variable.split("=")
        if not len(env_variable_list) == 2:
            self.ctx.log_err(
                f"Invalid environment variable: {env_variable}. Should be a key-value pair"
            )
            sys.exit(1)
        return env_variable_list[0], env_variable_list[1]

    def get_env_string(self, compose_env_dict={}):
        """Returns a string of key-value pairs from a dict."""

        compose_env_list = []
        for key, value in compose_env_dict.items():
            compose_env_list.append(f'{key}="{value}" ')
        return "".join(compose_env_list)


class Modules(object):
    def __init__(self, ctx):
        """
        Contains information about running Minipresto modules.
        """

        self.ctx = ctx
        (
            self.containers,
            self.module_label_vals,
            self.catalog,
            self.security,
        ) = self.get_running_modules()

    def get_running_modules(self):
        """Returns list of running modules."""

        docker_client = check_daemon()
        containers = self.get_running_containers(docker_client)
        module_label_vals = self.get_module_label_values(containers)
        catalog, security = self.parse_module_label_values(module_label_vals)

        return containers, module_label_vals, catalog, security

    def get_running_containers(self, docker_client):
        """Gets all running minipresto containers."""

        containers = docker_client.containers.list(filters={"label": RESOURCE_LABEL})
        if not containers:
            self.ctx.log_err(
                f"No running minipresto containers. To create a snapshot of an inactive environment, "
                f"you must specify the catalog and security modules. Run --help for more information."
            )
            sys.exit(1)
        return containers

    def get_module_label_values(self, containers=[]):
        """Gets all module label values from list of containers."""

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

    def parse_module_label_values(self, module_label_vals=[]):
        """
        Parses module label values and returns a tuple (space-delimited strings of
        both catalog and security modules) used to identify the correct directories
        to copy into the named snapshot directory.
        """

        catalog = []
        security = []

        for value in module_label_vals:
            if "catalog-" in value:
                catalog.append(value.strip().replace("catalog-", ""))
            elif "security-" in value:
                security.append(value.strip().replace("security-", ""))
            else:
                self.ctx.log_err(f"Invalid module label value {value}")
                sys.exit(1)
        return catalog, security


@pass_environment
def check_daemon(ctx):
    """Checks if the Docker daemon is running."""

    try:
        docker_client = docker.from_env()
        docker_client.ping()
        return docker_client
    except:
        ctx.log_err(
            f"Error when pinging the Docker server. Is the Docker daemon running?"
        )
        sys.exit(1)


@pass_environment
def validate_module_dirs(ctx, key, modules=[]):
    """
    Validates that the directory and Compose .yml exist for each provided
    module. If they all exist, a list of module directories and YAML file paths
    is returned.
    """

    module_type = key.get("module_type", "")
    module_dirs = []
    module_yaml_files = []

    for module in modules:
        module_dir = os.path.abspath(
            os.path.join(ctx.minipresto_lib_dir, MODULE_ROOT, module_type, module)
        )
        yaml_path = os.path.join(module_dir, f"{module}.yml")

        if not (os.path.isfile(yaml_path)):
            ctx.log_err(f"Invalid {module_type} module: {module}")
            sys.exit(1)
        module_dirs.append(module_dir)
        module_yaml_files.append(yaml_path)

    return module_dirs, module_yaml_files


def convert_MultiArgOption_to_list(*args):
    """
    Converts tuple datatype returned from the MultiArgOption to a list, as lists
    are the standard type used in the majority of the functions in Minipresto.
    """

    retval = []
    for arg in args:
        if not isinstance(arg, list):
            if arg == "":
                arg = []
                retval.append(arg)
            elif isinstance(arg, tuple):
                arg = list(arg)
                retval.append(arg)
        else:
            retval.append(arg)
    return tuple(retval)


def validate_yes_response(response):
    """Validates 'yes' user input."""

    response = response.replace(" ", "")
    if response.lower() == "y" or response.lower() == "yes":
        return True
    return False
