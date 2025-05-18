"""Command execution utilities for Minitrino clusters."""

from __future__ import annotations

import os
import re
import subprocess

from minitrino import utils
from minitrino.core.errors import MinitrinoError

from dataclasses import dataclass
from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class CommandExecutor:
    """
    Execute commands in the host shell or within Docker containers.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and context.

    Methods
    -------
    execute(*args, **kwargs)
        Execute commands in the user's shell or inside a container.
    """

    def __init__(self, ctx: MinitrinoContext) -> None:
        self._ctx = ctx

    def execute(self, *args: str, **kwargs) -> list[CommandResult]:
        """
        Execute commands in the user's shell or inside a Docker container.

        Parameters
        ----------
        *args : str
            One or more command strings to execute, in the order provided.
        **kwargs : dict
            Keyword arguments to pass to the subprocess or container.

        Returns
        -------
        list[CommandResult]
            A list of `CommandResult` objects, one per command.

        Notes
        -----
        Valid keyword arguments are:

        trigger_error : bool, optional
            If `False`, errors (non-zero exit codes) from executed commands will not
            raise an exception. Defaults to `True`.
        environment : dict, optional
            A dictionary of environment variables to pass to the subprocess or
            container.
        suppress_output : bool, optional
            If `True`, suppresses printing command output to stdout.
        container : docker.models.containers.Container, optional
            If provided, the command is executed inside the given Docker container.
        docker_user : str, optional
            The user to execute the command as within the Docker container. Defaults to
            `root`.
        """
        output: list[CommandResult] = []
        if kwargs.get("container", None):
            kwargs["environment"] = self._construct_environment(
                kwargs.get("environment", None), kwargs.get("container", None)
            )
            for command in args:
                output.append(self._execute_in_container(command, **kwargs))
        else:
            kwargs["environment"] = self._construct_environment(
                kwargs.get("environment", None)
            )
            for command in args:
                output.append(self._execute_in_shell(command, **kwargs))
        return output

    def _execute_in_shell(self, command: str, **kwargs) -> CommandResult:
        """
        Execute a command in the user's shell.

        Parameters
        ----------
        command : str
            The command string to execute.
        **kwargs : dict
            Keyword arguments to pass to the subprocess.

        Returns
        -------
        CommandResult
            The result of the command execution.
        """
        self._ctx.logger.verbose(
            f"Executing command in shell:\n{command}",
        )

        process = subprocess.Popen(
            command,
            shell=True,
            env=kwargs.get("environment", {}),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        if not kwargs.get("suppress_output", False):
            # Stream the output of the executed command line-by-line.
            # `universal_newlines=True` ensures output is generated as a string, so
            # there is no need to decode bytes. The only cleansing we need to do is to
            # run the string through the `_strip_ansi()` function.

            started_stream = False
            output = ""
            if process.stdout is not None:
                while True:
                    output_line = process.stdout.readline()
                    if output_line == "" and process.poll() is not None:
                        break
                    output_line = self._strip_ansi(output_line)
                    if not started_stream:
                        self._ctx.logger.verbose("Command Output:")
                        started_stream = True
                    self._ctx.logger.verbose(output_line, stream=True)
                    output += output_line
        else:
            output, _ = process.communicate()

        if process.returncode != 0 and kwargs.get("trigger_error", True):
            raise MinitrinoError(
                f"Failed to execute shell command:\n{command}\n"
                f"Exit code: {process.returncode}\n"
                f"Command output: {self._strip_ansi(output)}"
            )

        return CommandResult(
            command=command,
            output=self._strip_ansi(output),
            exit_code=process.returncode,
        )

    def _execute_in_container(self, command: str = "", **kwargs) -> CommandResult:
        """
        Execute a command inside a Docker container.

        Parameters
        ----------
        command : str
            The command to execute inside the container. Defaults to an empty string.
        **kwargs : dict
            Keyword arguments to pass to the subprocess.

        Returns
        -------
        CommandResult
            The result of the command execution.
        """
        container = kwargs.get("container", None)
        if container is None:
            raise MinitrinoError(
                f"Attempted to execute a command inside of a "
                f"container, but a container object was not provided."
            )

        if not kwargs.get("suppress_output"):
            self._ctx.logger.verbose(
                f"Executing command in container '{container.name}':\n{command}",
            )

        # Create exec handler and execute the command
        docker_user: str = kwargs.get("docker_user", "root")
        exec_handler = self._ctx.api_client.exec_create(
            container.name,
            cmd=command,
            environment=kwargs.get("environment", None),
            privileged=True,
            user=docker_user,
        )

        # `output` is a generator that yields response chunks
        output_generator = self._ctx.api_client.exec_start(exec_handler, stream=True)

        # Output from the generator is returned as bytes, so they need to be decoded to
        # strings. Response chunks are not guaranteed to be full lines. A newline in the
        # output chunk will trigger a log dump of the current `full_line` up to the
        # first newline in the current chunk. The remainder of the chunk (if any) resets
        # the `full_line` var, then log dumped when the next newline is received.

        output = ""
        full_line = ""
        started_stream = False
        for chunk in output_generator:
            chunk = self._strip_ansi(chunk.decode())
            output += chunk
            chunk = chunk.split("\n", 1)
            if len(chunk) > 1:  # Indicates newline present
                full_line += chunk[0]
                if not kwargs.get("suppress_output", False):
                    if not started_stream:
                        self._ctx.logger.verbose("Command Output:")
                        started_stream = True
                    self._ctx.logger.verbose(full_line, stream=True)
                    full_line = ""
                if chunk[1]:
                    full_line = chunk[1]
            else:
                full_line += chunk[0]

        # Catch lingering full line post-loop
        if not kwargs.get("suppress_output", False) and full_line:
            self._ctx.logger.verbose(full_line, stream=True)

        # Get the exit code
        exit_code = self._ctx.api_client.exec_inspect(exec_handler["Id"]).get(
            "ExitCode"
        )
        # https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html
        if exit_code == 126:
            self._ctx.logger.warn(
                f"The command exited with a 126 code which typically means an "
                f"executable is not accessible or installed. Does this image have "
                f"all required dependencies installed?\n"
                f"Command: {command}\n"
                f"Command output: {output}"
            )

        if exit_code != 0 and kwargs.get("trigger_error", True):
            raise MinitrinoError(
                f"Failed to execute command in container '{container.name}':\n{command}\n"
                f"Exit code: {exit_code}\n"
                f"Command output: {output}"
            )

        return cast(
            CommandResult,
            {"command": command, "output": output, "exit_code": exit_code},
        )

    def _construct_environment(
        self, environment: dict | None = None, container=None
    ) -> dict:
        """
        Construct the environment dictionary for command execution.

        Parameters
        ----------
        environment : dict, optional
            Additional environment variables to include.
        container : docker.models.containers.Container, optional
            The container for which to construct the environment.

        Returns
        -------
        dict
            The constructed environment dictionary.
        """
        if environment is None:
            environment = {}

        if not container:
            host_environment = os.environ.copy()
        else:
            host_environment_list = self._ctx.api_client.inspect_container(
                container.id
            )["Config"]["Env"]
            host_environment = {}
            for env_var in host_environment_list:
                k, v = utils.parse_key_value_pair(env_var)
                host_environment[k] = v

        if environment:
            delete_keys = []
            for host_key, _ in host_environment.items():
                for key, _ in environment.items():
                    if key == host_key:
                        delete_keys.append(host_key)
            for delete_key in delete_keys:
                del host_environment[delete_key]

        # Merge environment argument with copy of existing environment
        environment.update(host_environment)
        return environment

    def _strip_ansi(self, value: str = "") -> str:
        """
        Remove ANSI escape sequences from the given string.

        Parameters
        ----------
        value : str, optional
            Input string possibly containing ANSI escape codes.

        Returns
        -------
        str
            The cleaned string with ANSI codes removed.
        """
        # Strip ANSI codes before Click so that our logging helpers know if it's an
        # empty string or not.
        ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_regex.sub("", value)


@dataclass
class CommandResult:
    """
    Command result.

    Attributes
    ----------
    command : str
        The command string that was executed.
    output : str
        The combined output of stdout and stderr.
    exit_code : int
        The exit code returned by the command.
    """

    command: str
    output: str
    exit_code: int
