"""Utility functions for Minitrino CLI and core operations."""

from __future__ import annotations

import os
import sys
import traceback
from functools import wraps
from importlib.metadata import version
from inspect import signature
from typing import TYPE_CHECKING, Any, Dict, Optional

import docker
from click import echo, make_pass_decorator
from docker.models.containers import Container

from minitrino.core.docker.socket import resolve_docker_socket
from minitrino.core.docker.wrappers import MinitrinoContainer
from minitrino.core.errors import MinitrinoError, UserError
from minitrino.core.logger import LogLevel, MinitrinoLogger

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


def pass_environment() -> Any:
    """
    Return a Click pass decorator for the MinitrinoContext.

    Returns
    -------
    Any
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
    Handle a single exception.

    Parameters
    ----------
    error : Exception
        The exception object.
    ctx : Optional[Any]
        Optional CLI context object with logger.
    additional_msg : str
        Additional message to log, if any.
    skip_traceback : bool
        If True, suppresses traceback output unless overridden by error
        type.

    Raises
    ------
    SystemExit
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
    Handle unhandled exceptions.

    Parameters
    ----------
    func : Callable
        The function to wrap.

    Returns
    -------
    Callable
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
    Check if the Docker daemon is running.

    Parameters
    ----------
    docker_client : Any
        Docker client instance.

    Raises
    ------
    UserError
        If the Docker daemon is not running or cannot be pinged.
    """
    try:
        docker.DockerClient(base_url=resolve_docker_socket()).ping()
    except Exception as e:
        raise UserError(
            f"Error when pinging the Docker server. Is the Docker daemon running?\n"
            f"Error from Docker: {str(e)}",
            "You may need to initialize your Docker daemon. If Docker is already "
            "running, check whether you are using the intended Docker context "
            "(e.g. Colima or OrbStack). You can view existing contexts with `docker "
            "context ls` and switch with `docker context use <context>`.",
        )


def check_lib(ctx: MinitrinoContext) -> None:
    """
    Check if a Minitrino library exists.

    Parameters
    ----------
    ctx : MinitrinoContext
        Context object containing library directory information.
    """
    ctx.lib_dir


def container_user_and_id(
    ctx: Optional[MinitrinoContext] = None,
    container: Container | MinitrinoContainer | str = "",
) -> tuple[str, str]:
    """
    Return the build user and build user ID for a cluster container.

    Parameters
    ----------
    ctx : MinitrinoContext
        Context object containing cluster information.
    container : Container | MinitrinoContainer | str
        Container object or container name.

    Returns
    -------
    tuple[str, str]
        Tuple of build user and build user ID.

    Raises
    ------
    ValueError
        If container is not provided.

    Notes
    -----
    Commands executed in coordinator/worker containers tend to rely on
    environment variables set during the build process. This function
    returns the build user and build user ID for a cluster container,
    which can then be used to execute commands in the container with the
    correct UID to ensure environment variables resolve correctly.

    Examples
    --------
    >>> _, uid = container_user_and_id("minintrino-default")
    >>> cmd = "cat /etc/${CLUSTER_DIST}/config.properties"
    >>> cmd_executor.execute(
        f"bash -c '{cmd}'",
        container="minintrino-default",
        docker_user=uid,
    )
    """
    if not ctx:  # External call site, e.g. pytest
        from minitrino.core.context import MinitrinoContext

        ctx = MinitrinoContext()
        ctx.initialize(log_level=LogLevel.DEBUG)
    if not container:
        raise MinitrinoError("Container object or container name must be provided")
    if isinstance(container, str):
        container = ctx.cluster.resource.container(container)
    usr = ctx.cmd_executor.execute("bash -c 'echo $BUILD_USER'", container=container)[
        0
    ].output.strip()
    uid = ctx.cmd_executor.execute(f"bash -c 'id -u {usr}'", container=container)[
        0
    ].output.strip()
    return usr, uid


def generate_identifier(identifiers: Optional[Dict[str, Any]] = None) -> str:
    """
    Return an object identifier string used for creating log messages.

    Parameters
    ----------
    identifiers : Optional[Dict[str, Any]], optional
        Dictionary of "identifier_key": "identifier_value" pairs, by
        default None.

    Returns
    -------
    str
        Formatted string with identifiers enclosed in brackets.

    Examples
    --------
    >>> generate_identifier({"cluster": "default", "module": "test"})
    >>> '[cluster: default] [module: test]'
    """
    if identifiers is None:
        identifiers = {}
    identifier = []
    for key, value in identifiers.items():
        identifier.append(f"[{key}: {value}]")
    return " ".join(identifier)


def parse_key_value_pair(ctx: MinitrinoContext, pair: str) -> tuple[str, str]:
    """
    Parse a key-value pair from a string.

    Parameters
    ----------
    pair : str
        Key-value pair to parse.

    Returns
    -------
    tuple[str, str]
        Tuple of key and value.
    """
    pair = pair.strip()
    if "=" not in pair:
        ctx.logger.warn(f"Invalid key-value pair: {pair}")
        return "", ""
    key, value = pair.split("=", 1)
    return key, value


def cli_ver() -> str:
    """
    Return the CLI version.

    Returns
    -------
    str
        CLI version.
    """
    return version("Minitrino")


def lib_ver(ctx: Optional[MinitrinoContext] = None, lib_path: str = "") -> str:
    """
    Return the library version.

    Returns
    -------
    str
        Library version.
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


def validate_yes(value: str) -> bool:
    """
    Validate if the input is an affirmative response.

    Parameters
    ----------
    value : str
        Value to validate.

    Returns
    -------
    bool
        `True` if the input is 'y' or 'yes' (case-insensitive), `False`
        otherwise.
    """
    response = value.replace(" ", "")
    if response.lower() == "y" or response.lower() == "yes":
        return True
    return False
