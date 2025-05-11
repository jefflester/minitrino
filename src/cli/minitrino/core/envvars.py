#!/usr/bin/env python3

from __future__ import annotations

import os
import json

from minitrino import utils
from minitrino.core.errors import UserError
from minitrino.settings import CONFIG_TEMPLATE

from configparser import ConfigParser
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class EnvironmentVariables(dict):
    """
    Exposes all Minitrino environment variables.

    This class wraps environment variable handling for the CLI, combining
    user-provided input, OS environment variables, and values from the
    minitrino.cfg file.

    Constructor Parameters
    ----------------------
    `ctx` : `MinitrinoContext`
        An instantiated `MinitrinoContext` object containing user input and
        context.

    Methods
    -------
    Supports all `dict` methods: `get()` always returns a string.

    Examples
    --------
    >>> env_variable = ctx.env.get("CLUSTER_VER", "###-e")
    """

    def __init__(self, ctx: MinitrinoContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._parse_user_env()
        self._parse_os_env()
        self._parse_minitrino_config()

    def get(self, key: Any, default: Any = None) -> str:
        """Returns the value of the environment variable as a string."""
        val = super().get(key, default)
        return str(val) if val is not None else ""

    def _parse_user_env(self) -> None:
        """
        Parses user-provided environment variables for the current command.

        This method sets values from the list of user-supplied key-value pairs
        found in the calling `MinitrinoContext` object's `_user_env` attribute.
        These take first precedence when setting environment variables.

        Notes
        -----
        This is the highest-precedence source for setting variables in the
        `EnvironmentVariables` mapping.
        """

        if not self._ctx._user_env:
            return

        for env_var in self._ctx._user_env:
            k, v = utils.parse_key_value_pair(env_var, err_type=UserError)
            self[k] = v

    def _parse_os_env(self) -> None:
        """
        Parses environment variables from the user's shell.

        This method loads shell-level environment variables into the current
        `EnvironmentVariables` mapping. These variables take second precedence,
        falling back only if no user-provided values exist.

        Notes
        -----
        Environment variables parsed include common Minitrino-specific variables
        such as `CLUSTER_NAME`, `IMAGE`, and any library environment variable
        prefixed with `__PORT`. If a variable has already been set by
        `_parse_user_env`, it will not be overridden here.
        """

        shell_source = [
            "CLUSTER_NAME",
            "CLUSTER_VER",
            "CONFIG_PROPERTIES",
            "DOCKER_HOST",
            "IMAGE",
            "JVM_CONFIG",
            "LIB_PATH",
            "LIC_PATH",
            "TEXT_EDITOR",
        ]

        # Grab all minitrino.env vars that start with __PORT, then add the
        # variable names to the shell source list. If the file doesn't exist,
        # skip this step.
        try:
            lib_env = self._parse_library_env(dry_run=True)
            for k, v in lib_env.items():
                if k.startswith("__PORT"):
                    shell_source.append(k)
        except:
            pass

        for k, v in os.environ.items():
            k = k.upper()
            if k in shell_source and not self.get(k):
                self[k] = v

    def _parse_minitrino_config(self) -> None:
        """
        Parses the user's `minitrino.cfg` file and adds its values to the
        environment.

        This method reads the user's Minitrino config file and sets key-value
        pairs into the `EnvironmentVariables` mapping. These values take third
        precedence, after `_parse_user_env` and `_parse_os_env`.

        Notes
        -----
        Only variables from the `[config]` section of the config file are
        parsed. Keys are converted to uppercase before being added. Existing
        values are not overridden. If the config file is missing or malformed, a
        warning is logged and the method exits gracefully.
        """

        if not os.path.isfile(self._ctx.config_file):
            return

        try:
            config = ConfigParser(interpolation=None)
            config.__dict__["optionxform"] = str  # Make Mypy happy
            config.read(self._ctx.config_file)
            for k, v in config.items("config"):
                if not self.get(k) and v:
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

    def _parse_library_env(self, dry_run: bool = False) -> dict:
        """
        Parses the Minitrino library's `minitrino.env` file.

        This method loads environment variables from the `minitrino.env` file
        found in the active Minitrino library directory. These variables have
        the lowest precedence and are typically loaded during `initialize()`.

        If `dry_run` is `True`, the file is parsed and returned as a dictionary
        without modifying the current environment.

        Parameters
        ----------
        `dry_run` : `bool`, optional
            If `True`, environment variables will not be added to the current
            mapping. Defaults to `False`.

        Returns
        -------
        `dict`
            A dictionary of parsed key-value pairs from `minitrino.env`.

        Raises
        ------
        `UserError`
            If the `minitrino.env` file does not exist at the expected path.
        """

        env_file = os.path.join(self._ctx.lib_dir, "minitrino.env")
        if not os.path.isfile(env_file):
            raise UserError(
                f"Library 'minitrino.env' file does not exist at path: {env_file}",
                f"Are you pointing to a valid library, and is the minitrino.env file "
                f"present in that library?",
            )

        lib_env = {}
        with open(env_file, "r") as f:
            for env_var in f:
                k, v = utils.parse_key_value_pair(env_var, err_type=UserError)
                if not self.get(k):
                    if not dry_run:
                        self[k] = v
                    lib_env[k] = v

        return lib_env

    def _log_env_vars(self) -> None:
        """
        Logs the currently registered environment variables.

        If the `EnvironmentVariables` mapping contains any values, this method
        logs them in a pretty-printed JSON format using the `verbose` logger.
        """

        if self:
            self._ctx.logger.verbose(
                f"Registered environment variables:\n{json.dumps(self, indent=2)}",
            )
