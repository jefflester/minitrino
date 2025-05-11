#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import traceback
import pkg_resources

from minitrino.core.logger import MinitrinoLogger
from minitrino.core.errors import UserError, MinitrinoError

from functools import wraps
from inspect import signature
from click import echo, make_pass_decorator

from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


def pass_environment() -> Any:
    """
    Returns a Click pass decorator for the MinitrinoContext.

    Returns
    -------
    `Any`
        A decorator that passes the MinitrinoContext instance.
    """
    from minitrino.core.context import MinitrinoContext

    return make_pass_decorator(MinitrinoContext, ensure=True)


def handle_exception(
    error: Exception,
    ctx: Optional[Any] = None,
    additional_msg: str = "",
    skip_traceback: bool = False,
) -> None:
    """
    Handles a single exception. Wrapped by `@exception_handler` decorator.

    Parameters
    ----------
    `error` : `Exception`
        The exception object.
    `ctx` : `Optional[Any]`
        Optional CLI context object with logger.
    `additional_msg` : `str`
        Additional message to log, if any.
    `skip_traceback` : `bool`
        If True, suppresses traceback output unless overridden by error type.

    Raises
    ------
    `SystemExit`
        Exits the program with the appropriate exit code.
    """
    if isinstance(error, UserError):
        error_msg = error.msg
        exit_code = error.exit_code
        skip_traceback = True
    elif isinstance(error, MinitrinoError):
        error_msg = error.msg
        exit_code = error.exit_code
    else:
        error_msg = str(error)
        exit_code = 1

    logger = getattr(ctx, "logger", MinitrinoLogger())
    logger.error(additional_msg, error_msg)

    if not skip_traceback:
        echo()  # Force a newline
        echo(f"{traceback.format_exc()}", err=True)

    sys.exit(exit_code)


def exception_handler(func: Any) -> Any:
    """
    A decorator that handles unhandled exceptions with optional context access.

    Parameters
    ----------
    `func` : `Callable`
        The function to wrap.

    Returns
    -------
    `Callable`
        The wrapped function with exception handling.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        sig = signature(func)
        ctx = None
        if "ctx" in sig.parameters:
            try:
                ctx = kwargs.get("ctx") or args[list(sig.parameters).index("ctx")]
            except Exception:
                ctx = None

        try:
            return func(*args, **kwargs)
        except Exception as e:
            handle_exception(e, ctx)

    return wrapper


def check_daemon(docker_client: Any) -> None:
    """
    Checks if the Docker daemon is running. If an exception is thrown, it is
    handled.

    Parameters
    ----------
    `docker_client` : `Any`
        Docker client instance.

    Raises
    ------
    `UserError`
        If the Docker daemon is not running or cannot be pinged.
    """
    try:
        docker_client.ping()
    except Exception as e:
        raise UserError(
            f"Error when pinging the Docker server. Is the Docker daemon running?\n"
            f"Error from Docker: {str(e)}",
            f"You may need to initialize your Docker daemon. If Docker is already running, "
            f"check whether you are using the intended Docker context (e.g. Colima or OrbStack). "
            f"You can view existing contexts with `docker context ls` and switch with `docker "
            f"context use <context>`.",
        )


def check_lib(ctx: MinitrinoContext) -> None:
    """
    Checks if a Minitrino library exists.

    Parameters
    ----------
    `ctx` : `MinitrinoContext`
        Context object containing library directory information.
    """
    ctx.lib_dir


def generate_identifier(identifiers: Optional[Dict[str, Any]] = None) -> str:
    """
    Returns an 'object identifier' string used for creating log messages, e.g.
    '[ID: 12345] [Name: minitrino]'.

    Parameters
    ----------
    `identifiers` : `Optional[Dict[str, Any]]`, optional
        Dictionary of "identifier_key": "identifier_value" pairs, by default
        None.

    Returns
    -------
    `str`
        Formatted string with identifiers enclosed in brackets.

    Examples
    --------
    ```python identifier = generate_identifier(
        {"ID": container.short_id, "Name": container.name}
    ) # Output: "[ID: 12345] [Name: minitrino]" ```
    """
    if identifiers is None:
        identifiers = {}
    identifier = []
    for key, value in identifiers.items():
        identifier.append(f"[{key}: {value}]")
    return " ".join(identifier)


def parse_key_value_pair(
    kv_pair: str,
    err_type: Any = MinitrinoError,
    key_to_upper: bool = True,
) -> list[str]:
    """
    Parses a key-value pair in string form and returns the resulting pair as a
    list. Raises an exception if the string cannot be split by "=".

    Parameters
    ----------
    `kv_pair` : `str`
        A string formatted as a key-value pair, e.g. "CLUSTER_VER=388-e".
    `err_type` : `Exception` class, optional
        The exception to raise if an "=" delimiter is not in the key-value pair,
        by default MinitrinoError.
    `key_to_upper` : `bool`, optional
        If True, the key will be converted to uppercase, by default True.

    Returns
    -------
    `list[str]`
        A list `[key, value]` if parsing is successful.

    Raises
    ------
    `Exception` : `MinitrinoError` or `UserError`
        If the key-value pair is invalid or improperly formatted.
    """
    kv_pair = kv_pair.strip()
    if not kv_pair:
        return ["", ""]

    kv_pair_list = kv_pair.split("=", 1)
    err_msg = (
        f"Invalid key-value pair: '{'='.join(kv_pair_list)}'. "
        f"Key-value pairs should be formatted as 'KEY=VALUE'"
    )

    if not kv_pair_list or not kv_pair_list[0]:
        raise err_type(err_msg)

    for i in range(len(kv_pair_list)):
        kv_pair_list[i] = kv_pair_list[i].strip()
    if not kv_pair_list[0]:
        raise err_type(err_msg)
    elif key_to_upper:
        kv_pair_list[0] = kv_pair_list[0].upper()
    if not len(kv_pair_list) == 2:
        raise err_type(err_msg)

    return kv_pair_list


def cli_ver() -> str:
    """
    Returns the version of the Minitrino CLI.

    Returns
    -------
    `str`
        The CLI version string.
    """
    return pkg_resources.require("Minitrino")[0].version


def lib_ver(ctx: Optional[MinitrinoContext] = None, lib_path: str = "") -> str:
    """
    Returns the version of the Minitrino library.

    Parameters
    ----------
    `ctx` : `MinitrinoContext`, optional
        Partially initialized context object to extract library path from.
    `lib_path` : `str`, optional
        The Minitrino library directory, by default "".

    Returns
    -------
    `str`
        The version string if found, otherwise "NOT INSTALLED".
    """
    if ctx is None and not lib_path:
        raise ValueError("lib_path must be provided if ctx is None")

    if ctx is not None and not lib_path:
        lib_path = ctx.lib_dir

    version_file = os.path.join(lib_path, "version")
    try:
        with open(version_file, "r") as f:
            return next((line.strip() for line in f if line.strip()), "NOT INSTALLED")
    except Exception:
        return "NOT INSTALLED"


def validate_yes(response: str = "") -> bool:
    """
    Validates 'yes' user input.

    Parameters
    ----------
    `response` : `str`, optional
        The user input string, by default "".

    Returns
    -------
    `bool`
        True if the input is 'y' or 'yes' (case-insensitive), False otherwise.
    """
    response = response.replace(" ", "")
    if response.lower() == "y" or response.lower() == "yes":
        return True
    return False
