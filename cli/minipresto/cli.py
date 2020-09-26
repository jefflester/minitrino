#!usr/bin/env/python3
# -*- coding: utf-8 -*-

import os
import sys
import click
import docker

from pathlib import Path
from configparser import ConfigParser
from textwrap import fill
from shutil import get_terminal_size

from minipresto.exceptions import MiniprestoException
from minipresto.settings import DEFAULT_INDENT


CONTEXT_SETTINGS = dict(auto_envvar_prefix="MINIPRESTO")


class LogLevel:
    def __init__(self):
        """
        The level at which to log the message. The setting will affect the
        prefix color (i.e. the '[i]' in info messages is blue) and the prefix
        string (the string for the warn level is '[w]').

        Properties
        ----------
        - `info`
        - `warn`
        - `error`
        - `verbose`
        """

        self.info = {"prefix": "[i]  ", "prefix_color": "cyan"}
        self.warn = {"prefix": "[w]  ", "prefix_color": "yellow"}
        self.error = {"prefix": "[e]  ", "prefix_color": "red"}
        self.verbose = {"prefix": "[i]  ", "prefix_color": "cyan", "verbose": True}


class Environment:
    def __init__(self):
        """
        CLI Environment class.

        Properties
        ----------
        - `verbose`: Indicates whether or not output verbose logs to stdout.
        - `user_home_dir`: The home directory of the current user.
        - `minipresto_user_dir`: The location of the Minipresto directory
          relative to the user home directory.
        - `config_file`: The location of the user's configuration file.
        - `snapshot_dir`: The location of the user's snapshot directory (this is
          essentially a temporary directory, as 'permanent' snapshot tarballs
          are written to the library).
        - `minipresto_lib_dir`: The location of the Minipresto library
          directory.
        - `docker_client`: Docker client of object type `docker.DockerClient`
        - `api_client`: API Docker client of object type `docker.APIClient`

        Methods
        -------
        - `log()`: Log messages to the user's console.
        - `prompt_msg()`: Prints a prompt message and returns the user's input.
        - `get_config()`: Returns an instantiated ConfigParser object from the
          Minipresto user config. file.
        - `get_config_value()`: Returns a value from the config if present.
        """

        # Warnings
        self._initial_warnings = []

        # Verbose logging
        self.verbose = False

        # Paths
        self.user_home_dir = os.path.expanduser("~")
        self.minipresto_user_dir = self._handle_minipresto_user_dir()
        self.config_file = self._get_config_file()
        self.snapshot_dir = os.path.join(self.minipresto_user_dir, "snapshots")

        # Points to the directory containing minipresto library. Library
        # consists of modules, snapshots, and module parent files
        self.minipresto_lib_dir = self._get_minipresto_lib_dir()

        # Docker clients
        self.docker_client, self.api_client = self._get_docker_clients()

    def log(self, *args, level=LogLevel().info):
        """
        Logs messages to the user's console. Defaults to 'info' log level.

        Parameters
        ----------
        - `*args`: Messages to log.
        - `level`: The level of the log message.
        """

        # Skip verbose messages unless verbose mode is enabled
        if not self.verbose and level == LogLevel().verbose:
            return

        for msg in args:
            msg_split = msg.replace("\r", "\n").split("\n")
            for msg in msg_split:
                msg = self._transform_log_msg(msg)
                if not msg:
                    continue
                click.echo(
                    f"{click.style(level.get('prefix', ''), fg=level.get('prefix_color', ''), bold=True)}{msg}"
                )

    def _transform_log_msg(self, msg):
        if not isinstance(msg, str):
            raise MiniprestoException(
                f"Invalid type given to logger: [{msg}]. Message parameters must be a string."
            )

        msg = msg.rstrip()
        terminal_width, _ = get_terminal_size()
        msg = msg.replace("\n", f"\n{DEFAULT_INDENT}")
        msg = fill(
            msg,
            terminal_width,
            subsequent_indent=DEFAULT_INDENT,
            replace_whitespace=False,
            break_on_hyphens=False,
            break_long_words=False,
        )
        return msg

    def prompt_msg(self, msg="", input_type=str):
        """
        Prints a prompt message and returns the user's input.

        Parameters
        ----------
        - `msg`: The prompt message
        - `input_type`: The object type to check the input for
        """

        msg = self._transform_log_msg(msg)
        return click.prompt(
            f"{click.style(LogLevel().info.get('prefix', ''), fg=LogLevel().info.get('prefix_color', ''), bold=True)}{msg}",
            type=input_type,
        )

    def _handle_minipresto_user_dir(self):
        """
        Checks if a Minipresto directory exists in the user home directory. If
        it does not, it is created. The path to the Minipresto user home
        directory is returned.
        """

        minipresto_user_dir = os.path.abspath(
            os.path.join(self.user_home_dir, ".minipresto")
        )
        if not os.path.isdir(minipresto_user_dir):
            os.mkdir(minipresto_user_dir)
        return minipresto_user_dir

    def _get_config_file(self):
        """
        Returns the correct filepath for the minipresto.cfg file. Adds to
        initialization warnings if the file does not exist, but will return the
        path regardless.
        """

        config_file = os.path.join(self.minipresto_user_dir, "minipresto.cfg")
        if not os.path.isfile(config_file):
            self._initial_warnings.append(
                f"No minipresto.cfg file found in {config_file}. "
                f"Run 'minipresto config' to reconfigure this file and directory.",
            )
        return config_file

    def _get_minipresto_lib_dir(self):
        """
        Determines the directory of the Minipresto library. The directory can be
        set in three ways (this is also the order of precedence):
        1. The `-l` / `--lib-path` CLI option sets the library directory for the
           current command.
        2. The `minipresto.cfg` file's configuration sets the library directory
           if present.
        3. The CLI root is used to set the library directory and assumes the
           project is being run out of a cloned repository.
        """

        lib_dir = self.get_config_value("CLI", "LIB_PATH", False, None)
        if lib_dir:
            return lib_dir
        else:
            repo_root = Path(os.path.abspath(__file__)).resolve().parents[2]
            return os.path.join(repo_root, "lib")

    def get_config(self):
        """
        Returns an instantiated ConfigParser object from the Minipresto user
        config file.
        """

        if os.path.isfile(self.config_file):
            config = ConfigParser()
            config.optionxform = str  # Preserve case
            config.read(self.config_file)
            return config
        return {}

    def get_config_value(self, section="", key="", warn=True, default=None):
        """
        Returns a value from the config if present.

        Parameters
        ----------
        - `section`: The section of Minipresto user config.
        - `key`: The key for the desired value.
        - `warn`: If `True` and the value is not found, a warning message will
          be logged to the user.
        - `default`: The return value if the value is not found.
        """

        config = self.get_config()
        if config:
            try:
                value = config.get(section, key, fallback=default)
                return value
            except:
                if warn:
                    self.log(
                        f"Missing configuration section: [{section}] and/or key: [{key}]",
                        level=LogLevel().warn,
                    )
                return default
        return default

    def _get_docker_clients(self):
        """
        Gets DockerClient and APIClient objects. References the DOCKER_HOST
        variable in `minipresto.cfg` and uses for clients if present. Returns a
        tuple of DockerClient and APIClient objects, respectiveley.

        If there is an error fetching the clients, None types will be returned
        for each client. The lack of clients should be caught by check_daemon()
        calls that execute in each command that requires an accessible Docker
        service.
        """

        try:
            docker_host = self.get_config_value("DOCKER", "DOCKER_HOST", False, "")
            docker_client = docker.DockerClient(base_url=docker_host)
            api_client = docker.APIClient(base_url=docker_host)
            return docker_client, api_client
        # Daemon is likely not running and will be caught by check_daemon() calls
        except Exception as e:
            self._initial_warnings.append(
                f"Failed to obtain Docker client objects. This is likely because the Docker daemon is not running. "
                f"If Docker needs to be running, this will be caught by subsequent checks.\nError: {str(e)}"
            )
            return None, None

    def _log_initial_warnings(self):
        """
        Logs any warnings created during initialization. Should only be called
        when the CLI is initialized for a command.
        """

        if not self.verbose:
            return
        self.log(*self._initial_warnings, level=LogLevel().warn)


pass_environment = click.make_pass_decorator(Environment, ensure=True)
cmd_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "commands"))


class CLI(click.MultiCommand):
    def list_commands(self, ctx):
        retval = []
        for filename in os.listdir(cmd_dir):
            if filename.endswith(".py") and filename.startswith("cmd_"):
                retval.append(filename[4:-3])
        retval.sort()
        return retval

    def get_command(self, ctx, name):
        try:
            mod = __import__(f"minipresto.commands.cmd_{name}", None, None, ["cli"])
        except ImportError:
            return
        return mod.cli


@click.command(cls=CLI, context_settings=CONTEXT_SETTINGS)
@click.option("-v", "--verbose", is_flag=True, default=False, help="""
Enables verbose output.
""")
@click.option("-l", "--lib-path",
type=click.Path(exists=True, file_okay=False, resolve_path=True), help="""
Changes the command's library path.
""")


@pass_environment
def cli(ctx, verbose, lib_path):
    """Minipresto command line interface"""

    ctx.verbose = verbose
    ctx._log_initial_warnings()
    if lib_path:
        ctx.minipresto_lib_dir = lib_path
    ctx.log(f"Library path set to: {ctx.minipresto_lib_dir}", level=LogLevel().verbose)
