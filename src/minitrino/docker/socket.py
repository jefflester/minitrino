"""Resolve the Docker socket to use.

For internal and external use (e.g. CLI and tests).
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING, Any

from minitrino.errors import MinitrinoError

if TYPE_CHECKING:
    from minitrino.context import MinitrinoContext


def _inspect_active_context(
    ctx: MinitrinoContext | None, env: dict | os._Environ
) -> dict[str, Any] | None:
    """Run `docker context inspect` and return the first context entry, or None.

    Routes through `ctx.cmd_executor` when a context is provided, otherwise
    invokes the `docker` binary via subprocess. Returns None on any failure.
    """
    try:
        if ctx is None:
            stdout = subprocess.run(
                ["docker", "context", "inspect"],
                capture_output=True,
                check=True,
                text=True,
                env=env,
            ).stdout
        else:
            cmd_results = ctx.cmd_executor.execute(
                ["docker", "context", "inspect"],
                environment=env,
                suppress_output=True,
            )
            if not cmd_results:
                return None
            stdout = cmd_results[0].output
        parsed = json.loads(stdout)
        return parsed[0] if parsed else None
    except Exception:
        return None


def get_docker_context_name(ctx: MinitrinoContext | None = None, env=None) -> str:
    """Return the name of the active Docker context.

    Parameters
    ----------
    ctx : MinitrinoContext, optional
        The MinitrinoContext object to use for executing commands.
        Defaults to None.
    env : dict, optional
        Dictionary of environment variables to use when resolving the
        Docker context. Defaults to None.

    Returns
    -------
    str
        The name of the active Docker context (e.g., "orbstack",
        "desktop-linux", "default"). Returns empty string if unable to
        determine.
    """
    if env is None:
        env = os.environ
    context = _inspect_active_context(ctx, env)
    if context is None:
        return ""
    return context.get("Name", "")


def resolve_docker_socket(ctx: MinitrinoContext | None = None, env=None) -> str:
    """Return the Docker socket to use, preferring DOCKER_HOST if set.

    Parameters
    ----------
    ctx : MinitrinoContext, optional
        The MinitrinoContext object to use for executing commands.
        Defaults to None.
    env : dict, optional
        Dictionary of environment variables to use when resolving the
        Docker socket. Defaults to None.

    Returns
    -------
    str
        The Docker socket to use.

    Raises
    ------
    MinitrinoError
        If the Docker socket cannot be determined.
    """
    if env is None:
        env = os.environ
    socket_path = env.get("DOCKER_HOST")
    if socket_path:
        return socket_path
    context = _inspect_active_context(ctx, env)
    if context is None:
        raise MinitrinoError("Failed to determine Docker socket.")
    try:
        return context["Endpoints"]["docker"].get("Host", "")
    except (KeyError, TypeError) as e:
        raise MinitrinoError("Failed to determine Docker socket.") from e
