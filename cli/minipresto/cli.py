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

from minipresto.settings import DEFAULT_INDENT


CONTEXT_SETTINGS = dict(auto_envvar_prefix="MINIPRESTO")


class Environment:
    def __init__(self):
        """
        CLI Environment class.

        Properties
        ----------
        - `verbose`: Indicates whether or not output verbose logs to stdout.
        - `user_home_dir`: The home directory of the current user.
        - `minipresto_user_dir`: The location of the minipresto directory
          relative to the user home directory. 
        - `config_file`: The location of the user's configuration file. 
        - `snapshot_dir`: The location of the user's snapshot directory (this is
          essentially a temporary directory, as 'permanent' snapshot tarballs
          are written to the library).
        - `minipresto_lib_dir`: The location of the minipresto library
          directory.
        - `docker_client`: Docker client of object type `docker.DockerClient`
        - `api_client`: API Docker client of object type `docker.APIClient`

        Methods
        -------
        - `log()`: Log messages to the user's console.
        - `log_warn()`: Log warning messages to the user's console.
        - `log_err()`: Log error messages to the user's console.
        - `vlog()`: Log verbose messages to the user's console.
        - `prompt_msg()`: Prints a prompt message and returns the user's input.
        - `get_config()`: Returns an instantiated ConfigParser object from the
          Minipresto user config. file.
        - `get_config_value()`: Returns a value from the config if present.
        """

        # Verbose logging
        self.verbose = False

        # Paths
        self.user_home_dir = os.path.expanduser("~")
        self.minipresto_user_dir = self._handle_minipresto_user_dir()
        self.config_file = os.path.join(self.minipresto_user_dir, "minipresto.cfg")
        self.snapshot_dir = os.path.join(self.minipresto_user_dir, "snapshots")

        # Points to the directory containing minipresto library. Library
        # consists of modules, snapshots, and module parent files
        self.minipresto_lib_dir = self._get_minipresto_lib_dir()

        # Docker clients
        self.docker_client, self.api_client = self._get_docker_clients()

    def log(self, *args):
        """Logs messages to the user's console."""

        for arg in args:
            arg = self._transform_log_msg(arg)
            if arg:
                click.echo(
                    click.style(
                        f"[i]  {click.style(arg, fg='cyan', bold=False)}",
                        fg="cyan",
                        bold=True,
                    )
                )

    def log_warn(self, *args):
        """Logs warning messages to the user's console.."""

        for arg in args:
            arg = self._transform_log_msg(arg)
            if arg:
                click.echo(
                    click.style(
                        f"[w]  {click.style(arg, fg='yellow', bold=False)}",
                        fg="yellow",
                        bold=True,
                    )
                )

    def log_err(self, *args):
        """Logs error messages to the user's console."""

        for arg in args:
            arg = self._transform_log_msg(arg)
            if arg:
                click.echo(
                    click.style(
                        f"[e]  {click.style(arg, fg='red')}", fg="red", bold=True,
                    )
                )

    def vlog(self, *args):
        """Logs a message only if verbose logging is enabled."""

        if self.verbose:
            for arg in args:
                self.log(arg)

    def _transform_log_msg(self, msg):
        try:
            msg = msg.strip()
            if not msg:
                return None
        except:
            return None
        terminal_width, _ = get_terminal_size()
        msg = msg.replace("\n", f"\n{DEFAULT_INDENT}")
        msg = fill(
            msg,
            terminal_width,
            subsequent_indent=DEFAULT_INDENT,
            replace_whitespace=False,
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
        return click.prompt(
            click.style(
                f"[i]  {click.style(self._transform_log_msg(msg), fg='cyan', bold=False)}",
                fg="cyan",
                bold=True,
            ),
            type=input_type,
        )

    def _handle_minipresto_user_dir(self):
        """
        Checks if a minipresto directory exists in the user home directory. If
        it does not, it is created. The path to the minipresto user home
        directory is returned. 
        """

        minipresto_user_dir = os.path.abspath(
            os.path.join(self.user_home_dir, ".minipresto")
        )
        if not os.path.isdir(minipresto_user_dir):
            os.mkdir(minipresto_user_dir)
        return minipresto_user_dir

    def _get_minipresto_lib_dir(self):
        """
        Determines the directory of the minipresto library. The directory can be
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

    def get_config(self, warn=True):
        """
        Returns an instantiated ConfigParser object from the Minipresto user
        config file.

        Parameters
        ----------
        - `warn`: If `True` and the user configuration file does not exist, a
          warning message will be logged to the user.
        """

        if os.path.isfile(self.config_file):
            config = ConfigParser()
            config.optionxform = str  # Preserve case
            config.read(self.config_file)
            return config
        elif warn == True:
            self.log_warn(
                f"No minipresto.cfg file found in {self.config_file}. "
                f"Run 'minipresto config' to reconfigure this file and directory."
            )
        return {}

    def get_config_value(self, section="", key="", warn=True, default=None):
        """
        Returns a value from the config if present.

        Parameters
        ----------
        - `section`: The section of minipresto user config.
        - `key`: The key for the desired value.
        - `warn`: If `True` and the value is not found, a warning message will
          be logged to the user.
        - `default`: The return value if the value is not found.
        """

        config = self.get_config()
        if config:
            try:
                config = dict(config.items(section.upper()))
                value = config.get(key.upper())
                return value
            except:
                if warn:
                    self.log_warn(
                        f"Missing configuration section: [{section}] and/or key: [{key}]"
                    )
                return default

    def _get_docker_clients(self):
        """
        Gets DockerClient and APIClient objects. References the DOCKER_HOST
        variable in `minipresto.cfg` and uses for clients if present. Returns a
        tuple of DockerClient and APIClient objects, respectiveley.
        """

        docker_host = self.get_config_value("DOCKER", "DOCKER_HOST", False, "")
        docker_client = docker.DockerClient(base_url=docker_host)
        api_client = docker.APIClient(base_url=docker_host)
        return docker_client, api_client


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
    if lib_path:
        ctx.minipresto_lib_dir = lib_path
    ctx.vlog(f"Library path set to: {ctx.minipresto_lib_dir}")
