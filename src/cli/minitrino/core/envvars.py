"""Environment variable utilities for Minitrino clusters."""

from __future__ import annotations

import os
from configparser import ConfigParser
from typing import TYPE_CHECKING, Any

from minitrino import utils
from minitrino.core.errors import UserError
from minitrino.settings import CONFIG_TEMPLATE

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class EnvironmentVariables(dict):
    """Minitrino environment variables.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object containing user input
        and context.

    Methods
    -------
    get(key, default=None)
        Get an environment variable. Always returns a string.

    Examples
    --------
    >>> env_variable = ctx.env.get("CLUSTER_VER", "###-e")

    Notes
    -----
    This class bundles all environment variables used by Minitrino,
    combining user-provided input, OS environment variables, and values
    from the minitrino.cfg file.
    """

    def __init__(self, ctx: MinitrinoContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._parse_user_env_args()
        self._parse_os_env()
        self._parse_minitrino_config()

    def get(self, key: Any, default: Any = None) -> str:
        """Return the value for a given environment variable key.

        Parameters
        ----------
        key : Any
            The environment variable key.
        default : Any, optional
            The default value to return if the key is not found.
            Defaults to None.

        Returns
        -------
        str
            The value for the given environment variable key.
        """
        val = super().get(key, default)
        return str(val) if val is not None else ""

    def _strip_quotes(self, value: str) -> str:
        r"""Strip surrounding quotes from a string value.

        Removes matching single or double quotes from the beginning and end
        of a string. Only strips if both ends have the same quote character.

        Parameters
        ----------
        value : str
            The string value to process.

        Returns
        -------
        str
            The value with surrounding quotes removed, if applicable.

        Examples
        --------
        >>> env._strip_quotes('"hello"')
        'hello'
        >>> env._strip_quotes("'world'")
        'world'
        >>> env._strip_quotes('"mixed\\'')
        '"mixed\\'
        >>> env._strip_quotes('no-quotes')
        'no-quotes'

        Notes
        -----
        This method only strips quotes from values parsed from the
        minitrino.cfg configuration file. It does not affect user-provided
        command-line arguments or OS environment variables.
        """
        value = value.strip()
        if len(value) >= 2 and (
            (value[0] == '"' and value[-1] == '"')
            or (value[0] == "'" and value[-1] == "'")
        ):
            return value[1:-1]
        return value

    def _parse_user_env_args(self) -> None:
        """Parse user-specified environment variables from the config file.

        Notes
        -----
        This is the highest-precedence source for setting variables in
        the EnvironmentVariables mapping.
        """
        if not self._ctx._user_env_args:
            return

        for env_var in self._ctx._user_env_args:
            k, v = utils.parse_key_value_pair(self._ctx, env_var, hard_fail=True)
            self[k.upper()] = str(v)

    def _parse_os_env(self) -> None:
        """Parse environment variables from the user's shell.

        Notes
        -----
        These variables take second precedence, falling back only if no
        user-provided values exist.

        Environment variables parsed include common Minitrino-specific
        variables such as `CLUSTER_NAME`, `IMAGE`, and any library
        environment variable prefixed with `__PORT`. If a variable has
        already been set by `_parse_user_env_args`, it will not be overridden
        here.
        """
        shell_source = [
            "CLUSTER_NAME",
            "CLUSTER_VER",
            "COMPOSE_BAKE",
            "CONFIG_PROPERTIES",
            "WORKER_CONFIG_PROPERTIES",
            "DOCKER_HOST",
            "IMAGE",
            "JVM_CONFIG",
            "WORKER_JVM_CONFIG",
            "KEEP_PLUGINS",
            "LIB_PATH",
            "LIC_PATH",
            "PROVISION_BUILD_TIMEOUT",
            "STARTUP_SELECT_RETRIES",
            "TEXT_EDITOR",
        ]
        for k, v in os.environ.items():
            k = k.upper()
            if k in shell_source and not self.get(k):
                self[k] = str(v)

    def _parse_minitrino_config(self) -> None:
        """Parse the user's `minitrino.cfg` file.

        Notes
        -----
        These values take third precedence, after `_parse_user_env_args` and
        `_parse_os_env`.

        Only variables from the `[config]` section of the config file
        are parsed. Keys are converted to uppercase before being added.
        Existing values are not overridden. If the config file is
        missing or malformed, a warning is logged and the method exits
        gracefully.
        """
        if not os.path.isfile(self._ctx.config_file):
            return

        try:
            config = ConfigParser(interpolation=None)
            config.__dict__["optionxform"] = str  # Make Mypy happy
            config.read(self._ctx.config_file)
            for k, v in config.items("config"):
                if not self.get(k) and v:
                    self[k.upper()] = self._strip_quotes(str(v))
        except Exception as e:
            self._ctx.logger.warn(
                f"Failed to parse config file {self._ctx.config_file} with error:"
                f"\n{str(e)}\n"
                f"Variables set in the config file will not be loaded. You can "
                f"reset your configuration file with minitrino config --reset or "
                f"edit it manually with minitrino config. The valid config file "
                f"structure is:\n"
                f"{CONFIG_TEMPLATE}"
            )
            return

    def _parse_library_env(self) -> dict:
        """Parse the Minitrino library's `minitrino.env` file.

        Returns
        -------
        dict
            A dictionary of parsed key-value pairs from `minitrino.env`.

        Raises
        ------
        UserError
            If the `minitrino.env` file does not exist at the expected
            path.

        Notes
        -----
        These variables have the lowest precedence and are typically
        loaded during `initialize()`. The method loads environment
        variables from the `minitrino.env` file found in the active
        Minitrino library directory.
        """
        env_file = os.path.join(self._ctx.lib_dir, "minitrino.env")
        if not os.path.isfile(env_file):
            raise UserError(
                f"Library 'minitrino.env' file does not exist at path: {env_file}",
                "Are you pointing to a valid library, and is the minitrino.env file "
                "present in that library?",
            )

        lib_env = {}
        with open(env_file) as f:
            for env_var in f:
                if not env_var.strip():
                    continue
                k, v = utils.parse_key_value_pair(self._ctx, env_var)
                k = k.upper()
                if not self.get(k):
                    self[k] = str(v)
                    lib_env[k] = str(v)

        return lib_env

    def _log_env_vars(self) -> None:
        """Log the currently-registered environment variables.

        Notes
        -----
        If the `EnvironmentVariables` mapping contains any values, this
        method logs them in a pretty-printed JSON format using the
        `debug` logger.
        """
        if self:
            sorted_items = sorted(self.items())
            # Find max key length for alignment
            max_key_len = max(len(str(k)) for k, _ in sorted_items)
            env_lines = []
            pad = 4  # extra spaces after the longest key
            for k, v in sorted_items:
                key_str = str(k)
                spaces = " " * (max_key_len - len(key_str) + pad)
                env_lines.append(f"\t{key_str}{spaces}{v}")
            env_block = "\n".join(env_lines)
            self._ctx.logger.debug(f"Registered environment variables:\n{env_block}")
