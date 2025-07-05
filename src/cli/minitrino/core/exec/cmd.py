"""Command execution utilities for Minitrino clusters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

from minitrino.core.errors import MinitrinoError
from minitrino.core.exec.container import ContainerCommandExecutor
from minitrino.core.exec.host import HostCommandExecutor
from minitrino.core.exec.result import CommandResult

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class CommandExecutor:
    """
    Execute commands in a subprocess or within a Docker container.

    This is a thin dispatcher that delegates to HostCommandExecutor or
    ContainerCommandExecutor based on the presence of the 'container'
    kwarg.
    """

    def __init__(self, ctx: "MinitrinoContext") -> None:
        self._ctx = ctx

    def execute(
        self,
        *args: list[str],
        **kwargs: Any,
    ) -> list[CommandResult]:
        """
        Execute commands in a subprocess or within a container.

        Keyword Arguments
        -----------------
        interactive : bool
            If True, runs the command in interactive mode.
        container : MinitrinoContainer
            The container to run the command in. If not provided, the
            command will be run on the host via HostCommandExecutor.
        user : str
            The user to run the command as. If not provided, the command
            will be run as root.
        environment : dict
            The environment variables to pass to the command.
        suppress_output : bool
            If True, suppresses output from the command.
        trigger_error : bool
            If True, raises an error if the command fails. Defaults to
            False.
        timeout : float
            The timeout for the command.
        """
        interactive = kwargs.pop("interactive", False)
        results = []
        for command in args:
            try:
                if kwargs.get("container", None):
                    result = ContainerCommandExecutor(self._ctx).execute(
                        command, **kwargs
                    )
                else:
                    result = HostCommandExecutor(self._ctx).execute(
                        command,
                        interactive=interactive,
                        **kwargs,
                    )
                results.append(result)
            except Exception as error:
                results.append(
                    CommandResult(
                        command,
                        output="",
                        exit_code=-1,
                        duration=0.0,
                        error=error,
                    )
                )
        return results

    def stream_execute(
        self,
        *args: list[str],
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        Stream output from subprocesses or commands inside containers.

        Parameters
        ----------
        *args : list[str]
            A list of arguments to pass to the subprocess or container.
        **kwargs : dict
            Keyword arguments to pass to the subprocess or container.

        Yields
        ------
        str
            Output lines as they are produced by the command(s).
        """
        interactive = kwargs.pop("interactive", False)
        for command in args:
            if kwargs.get("container", None):
                yield from ContainerCommandExecutor(self._ctx).stream_execute(
                    command, **kwargs
                )
            else:
                if not isinstance(command, list):
                    raise MinitrinoError(
                        "Host commands must be passed as a list of arguments. "
                        f"Got: {command!r}"
                    )
                yield from HostCommandExecutor(self._ctx).stream_execute(
                    command,
                    interactive=interactive,
                    **kwargs,
                )
