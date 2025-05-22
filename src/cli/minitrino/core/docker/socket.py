"""
Resolve the Docker socket to use.

For internal and external use (e.g. CLI and tests).
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING, Optional

from minitrino.core.errors import MinitrinoError

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


def resolve_docker_socket(ctx: Optional[MinitrinoContext] = None, env=None) -> str:
    """
    Return the Docker socket to use, preferring DOCKER_HOST if set.

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
    try:
        if ctx is None:
            subproc_result = subprocess.run(
                ["docker", "context", "inspect"],
                capture_output=True,
                check=True,
                text=True,
                env=env,
            )
            stdout = subproc_result.stdout
        else:
            cmd_result = ctx.cmd_executor.execute(
                "docker context inspect", environment=env, suppress_output=True
            )[0]
            stdout = cmd_result.output
        context = json.loads(stdout)[0]
        return context["Endpoints"]["docker"].get("Host", "")
    except Exception as e:
        raise MinitrinoError(f"Failed to determine Docker socket: {e}")
