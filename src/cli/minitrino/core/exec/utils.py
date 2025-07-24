"""Command execution utilities for Minitrino clusters."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from minitrino.core.cluster.resource import MinitrinoContainer
from minitrino.core.errors import MinitrinoError

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


def detect_container_shell(
    ctx: MinitrinoContext, container: MinitrinoContainer | str, user: str = "root"
) -> str:
    """
    Detect the shell in the container.

    Waits up to 10 seconds for the container to accept commands.

    Parameters
    ----------
    ctx : MinitrinoContext
        The Minitrino context.
    container : MinitrinoContainer | str
        The container  (or fully qualified container name) to detect the
        shell for.
    user : str, optional
        The user to execute shell detection as (default is "root").

    Raises
    ------
    MinitrinoError
        If the container does not accept commands within 10 seconds, or
        no shell is found.
    """
    timeout = 10.0
    poll_interval = 0.2
    start = time.monotonic()
    last_e: Exception | None = None
    fqcn = container if isinstance(container, str) else container.name

    while time.monotonic() - start < timeout:
        try:
            container_obj = _get_container(ctx, container)
        except Exception as e:
            last_e = e
            time.sleep(poll_interval)
            continue
        if container_obj.status != "running":
            time.sleep(poll_interval)
            continue
        try:
            return _check_shell(ctx, container_obj, user)
        except Exception as e:
            last_e = e
            time.sleep(poll_interval)
            continue
    raise MinitrinoError(
        f"Container '{fqcn}' could not accept commands or does not have a shell "
        f"installed within {timeout:.1f} seconds."
    ) from last_e


def _get_container(
    ctx: MinitrinoContext, container: MinitrinoContainer | str
) -> MinitrinoContainer:
    """Get the container object."""
    if isinstance(container, str):
        container_obj = ctx.cluster.resource.container(container)
    else:
        container_obj = ctx.cluster.resource.container(container.name)
    return container_obj


def _check_shell(
    ctx: MinitrinoContext, container: MinitrinoContainer, user: str
) -> str:
    """Check for and return a working shell in the container."""
    last_e: Exception
    shells = [
        "bash",
        "/bin/bash",
        "/usr/bin/bash",
        "sh",
        "/bin/sh",
        "/usr/bin/sh",
    ]
    for shell in shells:
        try:
            ctx.logger.debug(
                f"Checking for shell '{shell}' in container '{container.name}'"
            )
            result = container.exec_run([shell, "-c", "echo ok"], user=user)
            if result.exit_code == 0 and b"ok" in result.output:
                return shell
            raise MinitrinoError(
                f"Shell '{shell}' does not exist or is not executable. "
                f"Command output: {result.output.decode('utf-8')}",
            )
        except Exception as e:
            last_e = e
            continue
    raise last_e
