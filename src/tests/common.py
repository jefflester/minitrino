"""Common utilities for Minitrino integration and system tests."""

import contextlib
import logging
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from time import sleep

import docker
from click.testing import CliRunner, Result
from docker.models.containers import Container
from minitrino.ansi import strip_ansi
from minitrino.cli import cli
from minitrino.core.docker.socket import get_docker_context_name, resolve_docker_socket
from minitrino.settings import ROOT_LABEL

USER_HOME_DIR = os.path.expanduser("~")
MINITRINO_USER_DIR = os.path.abspath(os.path.join(USER_HOME_DIR, ".minitrino"))
CONFIG_FILE = os.path.abspath(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg"))
MINITRINO_LIB_DIR = os.path.join(
    Path(os.path.abspath(__file__)).resolve().parents[2], "lib"
)

# ------------------------
# Logging Utilities
# ------------------------


def get_logger(log_level: int | None = None) -> logging.Logger:
    """Get or create the logger for the test module.

    If the logger has already been created, always set its log level if
    log_level is provided. Otherwise, use the environment variable or
    INFO.

    Parameters
    ----------
    log_level : int | None
        The log level to use for the logger. Defaults to the value of
        the `MINITRINO_TEST_LOG_LEVEL` environment variable, or
        `logging.INFO` if not set.
    """
    # Reset logger class to standard Python logger to avoid conflicts
    # with Minitrino's custom MinitrinoLogger class that may be set globally
    original_logger_class = logging.getLoggerClass()
    logging.setLoggerClass(logging.Logger)

    try:
        logger = logging.getLogger("test.minitrino")
        if isinstance(log_level, int):
            logger.setLevel(log_level)
        elif not logger.hasHandlers():
            env_log_level: str | int = os.environ.get(
                "MINITRINO_TEST_LOG_LEVEL", logging.INFO
            )
            if isinstance(env_log_level, str):
                env_log_level = env_log_level.strip()
            logger.setLevel(env_log_level)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(levelname)-8s %(name)s:%(filename)s:%(lineno)d %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    finally:
        # Restore the original logger class
        logging.setLoggerClass(original_logger_class)


logger: logging.Logger = get_logger()

# ------------------------
# CLI Command Helpers
# ------------------------


class MinitrinoExecutor:
    """Minitrino CLI command builder and executor.

    Parameters
    ----------
    cluster : str
        The cluster name to use.
    debug : bool
        Whether to enable debug logging.

    Methods
    -------
    build_cmd
        Build a CLI command for CliRunner.
    exec
        Log and execute a CLI command.
    """

    def __init__(self, cluster: str, debug: bool = False):
        self.cluster = cluster
        self.debug = debug

    def build_cmd(
        self,
        base: str = "",
        cluster: str = "",
        append: list[str] | None = None,
        prepend: list[str] | None = None,
        debug: bool | None = None,
    ) -> list[str]:
        """Build a CLI command for CliRunner.

            [minitrino (<impl>)] [-v] [--cluster <cluster>] <prepend>
            <base> <append>

        Parameters
        ----------
        base : str
            The base command (e.g. 'down', 'remove').
        cluster : str
            The cluster name to use. Defaults to the cluster name
            specified in the constructor.
        append : list[str]
            Extra arguments to add to the command after the base
            command.
        prepend : list[str]
            Extra arguments to add to the command before the base
            command.
        debug : Optional[bool]
            Whether to enable debug logging. Defaults to the value of
            the `debug` attribute of the executor.

        Returns
        -------
        list[str]
            The built command.

        Examples
        --------
        >>> build_cmd("down")
        ["-v", "--cluster", "cli-test", "down"]
        >>> build_cmd("down", cluster="cli-test-2")
        ["-v", "--cluster", "cli-test-2", "down"]
        >>> build_cmd("down", append=["--sig-kill"], prepend=["--env", "FOO=bar"])
        ["-v", "--cluster", "cli-test", "--env", "FOO=bar", "down", "--sig-kill"]
        """
        append = append or []
        prepend = prepend or []
        # Build command - base is optional for flags like --version
        if base:
            cmd = ["--cluster", cluster or self.cluster, *prepend, base, *append]
        else:
            # No base command - omit --cluster (e.g., for --version flag)
            cmd = [*prepend, *append]
        if self.debug or debug:
            cmd = ["-v"] + cmd
        cmd = [  # Filter invalid arguments
            s
            for s in cmd
            if isinstance(s, str) and s.strip() or isinstance(s, (int, float))
        ]
        return cmd

    def exec(
        self,
        cmd: list[str],
        input: str | None = None,
        env: dict[str, str] | None = None,
        log_output: bool = True,
    ) -> Result:
        """Log and execute a CLI command.

        Parameters
        ----------
        cmd : list[str]
            The command and arguments to invoke.
        input : str | None
            Input string to pass to the command (for prompts, etc.).
            Defaults to None.
        env : Optional[Dict[str, str]]
            Environment variables to set for the command. Defaults to an
            empty dict.
        log_output : bool
            Whether to log the output of the command. Defaults to True.

        Returns
        -------
        Result
            The Click testing Result object.
        """
        msg = "Invoking CLI command '%s' %s"
        if log_output:
            logger.debug(
                msg
                % (
                    f"minitrino {' '.join(cmd) if cmd else ''}",
                    f" with input: {input}" if input else "",
                )
            )
        # Mix stderr into stdout so logs are captured in result.output
        runner = CliRunner(mix_stderr=True)
        env = env or {}
        result = runner.invoke(cli, cmd, input=input, env=env)
        if log_output:
            logger.debug(f"Result output:\n{result.output.rstrip()}")
        return result


# ------------------------
# Docker Helpers
# ------------------------


def is_docker_running() -> bool:
    """Check if the Docker daemon is currently running and accessible.

    Returns
    -------
    bool
        True if Docker is running and responding to a ping, False
        otherwise.
    """
    try:
        docker.DockerClient(base_url=resolve_docker_socket()).ping()
        return True
    except Exception as e:
        msg = f"Failed to ping Docker daemon: {e}"
        logger.warning(msg)
        return False


def try_start(cmd: list[str]) -> bool:
    """Attempt to start a process using the provided command.

    Parameters
    ----------
    cmd : list of str
        The command and arguments to execute.

    Returns
    -------
    bool
        True if the command executed successfully (exit code 0), False
        otherwise.
    """
    try:
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        result = execute_cmd(cmd=cmd_str)
        return result.exit_code == 0
    except Exception:
        return False


def start_docker_daemon(context: str | None = None) -> None:
    """Start the Docker daemon on macOS or Linux.

    Parameters
    ----------
    context : str, optional
        The Docker context name to use (e.g., "orbstack", "desktop-linux").
        If provided, will start the backend matching this context.
        If not provided, will detect the active context.

    Raises
    ------
    RuntimeError
        If no supported Docker backend is found or the platform is
        unsupported.
    TimeoutError
        If the Docker daemon does not start within one minute.

    Notes
    -----
    Supports Docker Desktop, OrbStack, Colima, Rancher Desktop, etc.

    This function will detect the available Docker backend and attempt
    to start it if Docker is not already running. It waits up to 60
    seconds for Docker to become available.

    The function respects the active Docker context and will prioritize
    starting the backend associated with that context.
    """
    if is_docker_running():
        return

    started = False
    if sys.platform.lower() == "darwin":
        # Use provided context or detect the active context
        active_context = context if context else get_docker_context_name()

        # Try to start the backend matching the active context first
        if "orbstack" in active_context.lower() and shutil.which("orbstack"):
            started = try_start(["open", "-a", "OrbStack"])
        elif "colima" in active_context.lower() and shutil.which("colima"):
            started = try_start(["colima", "start"])
        elif "rancher" in active_context.lower() and shutil.which("rancher-desktop"):
            started = try_start(["open", "-a", "Rancher Desktop"])
        elif (
            ("desktop" in active_context.lower() or "default" in active_context.lower())
            and shutil.which("docker")
            and shutil.which("open")
        ):
            started = try_start(["open", "--background", "-a", "Docker"])

        # Fallback: Only retry the backend that matches the active context
        # Don't switch to a different backend automatically
        if not started:
            if "orbstack" in active_context.lower() and shutil.which("orbstack"):
                started = try_start(["open", "-a", "OrbStack"])
            elif "colima" in active_context.lower() and shutil.which("colima"):
                started = try_start(["colima", "start"])
            elif "rancher" in active_context.lower() and shutil.which(
                "rancher-desktop"
            ):
                started = try_start(["open", "-a", "Rancher Desktop"])
            elif (
                (
                    "desktop" in active_context.lower()
                    or "default" in active_context.lower()
                )
                and shutil.which("docker")
                and shutil.which("open")
            ):
                started = try_start(["open", "--background", "-a", "Docker"])

        if not started:
            raise RuntimeError(
                f"Failed to start Docker backend for context "
                f"'{active_context}'. Supported backends: Docker Desktop, "
                f"OrbStack, Colima, Rancher Desktop."
            )
    elif "linux" in sys.platform.lower():
        if shutil.which("systemctl"):
            started = try_start(["sudo", "systemctl", "start", "docker"])
        if not started and shutil.which("service"):
            started = try_start(["sudo", "service", "docker", "start"])
        if not started:
            raise RuntimeError(
                "Could not start Docker daemon (systemctl/service not available)."
            )
    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")

    for _ in range(60):
        if is_docker_running():
            return
        sleep(1)
    raise TimeoutError("Docker daemon failed to start after one minute.")


def try_stop(cmd: list[str]) -> bool:
    """Attempt to stop a process or service using the provided command.

    Parameters
    ----------
    cmd : list of str
        The command and arguments to execute.

    Returns
    -------
    bool
        True if the command executed successfully (exit code 0), False
        otherwise.
    """
    try:
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        result = execute_cmd(cmd=cmd_str)
        return result.exit_code == 0
    except Exception:
        return False


def force_quit_docker_backends():
    """Immediately quit all known Docker backends on macOS.

    Tries AppleScript for graceful quit, then killall for UI and backend processes. No
    sudo required. For Colima, uses 'colima stop'.
    """
    import shutil
    from time import sleep

    for app in ["Docker", "OrbStack", "Rancher Desktop"]:
        if shutil.which("osascript"):
            with contextlib.suppress(Exception):
                execute_cmd(cmd=f"osascript -e 'quit app \"{app}\"'")
    sleep(2)
    for proc in [
        "Docker",
        "com.docker.backend",
        "com.docker.hyperkit",
        "OrbStack",
        "com.orbstack.backend",
        "com.orbstack.hyperkit",
        "Rancher Desktop",
        "lima",
        "qemu-system-aarch64",
        "qemu-system-x86_64",
    ]:
        with contextlib.suppress(Exception):
            execute_cmd(cmd=f"killall -9 {proc}")
    if shutil.which("colima"):
        execute_cmd(cmd="colima stop")


def stop_docker_daemon() -> None:
    """Force-stop the Docker daemon.

    Raises
    ------
    RuntimeError
        If no supported Docker backend is found or the platform is
        unsupported.
    TimeoutError
        If the Docker daemon does not stop within one minute.
    """
    if sys.platform.lower() == "darwin":
        force_quit_docker_backends()
    elif "linux" in sys.platform.lower():
        stopped = False
        if shutil.which("systemctl"):
            stopped = try_stop(["sudo", "systemctl", "stop", "docker"])
        if not stopped and shutil.which("service"):
            stopped = try_stop(["sudo", "service", "docker", "stop"])
        if not stopped:
            cmd_str = " ".join(
                shlex.quote(arg) for arg in ["sudo", "killall", "-9", "dockerd"]
            )
            execute_cmd(cmd=cmd_str)

    else:
        raise RuntimeError(f"Incompatible testing platform: {sys.platform}")

    for _ in range(60):
        if not is_docker_running():
            return
        sleep(1)
    raise TimeoutError("Docker daemon failed to stop after 60 seconds.")


def get_containers(container_name: str = "", all: bool = False) -> list[Container]:
    """Fetch Minitrino containers.

    If a name is provided, return the container with the specified name.
    If no name is provided, return all containers.

    Parameters
    ----------
    container_name : str
        Name of the container to fetch.
    all : bool
        Whether to fetch all containers or only running containers.

    Returns
    -------
    list[Container]
        List of containers if `container_name` is not provided,
        otherwise the container with the specified name.

    Raises
    ------
    RuntimeError
        If the container is not found.
    """
    time.sleep(1)  # Avoid race condition
    docker_client = docker.DockerClient(base_url=resolve_docker_socket())

    containers: list[Container] = docker_client.containers.list(
        filters={"label": [ROOT_LABEL]}, all=all
    )
    if not container_name:
        return containers
    for container in containers:
        if container.name == container_name:
            return [container]
    raise RuntimeError(f"Container '{container_name}' not found")


def execute_in_coordinator(cmd: str = "", container_name: str = "") -> "CommandResult":
    """Execute a command in the coordinator container.

    Parameters
    ----------
    cmd : str
        The command to execute.

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit
        code.
    """
    from minitrino.utils import container_user_and_id

    _, uid = container_user_and_id(container=container_name)
    wrapped_cmd = f"bash -c {shlex.quote(cmd)}"
    return execute_cmd(wrapped_cmd, container_name, user=uid)


# ------------------------
# Command Helpers
# ------------------------


@dataclass
class CommandResult:
    """Command result.

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


def execute_cmd(
    cmd: str = "",
    container: str | None = None,
    env: dict[str, str] | None = None,
    user: str = "root",
) -> CommandResult:
    """Execute a command in the user's shell or inside of a container.

    Parameters
    ----------
    cmd : str
        The command to execute.
    container : str, optional
        Container name to execute command inside of.
    env : dict[str, str], optional
        Environment variables to pass to the container.
    user : str, optional
        The user (or user ID) to execute the command as within the
        container. Defaults to `root`.

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit
        code.
    """
    env = env or {}
    if container:
        return _execute_in_container(cmd, container, env, user)
    else:
        return _execute_in_shell(cmd, env)


def _execute_in_shell(
    cmd: str = "", env: dict[str, str] | None = None
) -> CommandResult:
    """Execute a command in the host shell.

    Parameters
    ----------
    cmd : str
        The command to execute.
    env : dict[str, str], optional
        Environment variables to use for the command.

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit
        code.
    """
    logger.debug(f"Executing command in host shell: {cmd}")

    env = env or {}
    process = subprocess.Popen(
        cmd,
        shell=True,
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        env={**os.environ, **env},
    )

    output = ""
    logger.debug("Command output:")
    if process.stdout is None:
        raise RuntimeError(f"Failed to execute command: {cmd}")
    with process.stdout as p:
        for line in p:
            output += line
            logger.debug(line.rstrip())
    process.wait()
    return CommandResult(cmd, output, process.returncode)


def _execute_in_container(
    cmd: str = "",
    container_name: str = "",
    env: dict[str, str] | None = None,
    user: str = "root",
) -> CommandResult:
    """Execute a command inside of a container.

    Parameters
    ----------
    cmd : str
        The command to execute.
    container_name : str
        Name of the container to execute the command in.
    env : dict[str, str], optional
        Environment variables to use for the command.
    user : str, optional
        The user (or user ID) to execute the command as within the
        container. Defaults to `root`.

    Returns
    -------
    CommandResult
        Command result object containing the command output and exit
        code.
    """
    api_client = docker.APIClient(base_url=resolve_docker_socket())
    container = get_containers(container_name)[0]

    logger.debug(f"Executing command in container '{container.name}': {cmd}")

    env = env or {}
    exec_handler = api_client.exec_create(
        container.name,
        cmd=f"bash -c {shlex.quote(cmd)}",
        environment=env,
        privileged=True,
        user=user,
    )

    output_generator = api_client.exec_start(exec_handler, stream=True)

    output = ""
    full_line = ""
    logger.debug("Command output:")
    for chunk in output_generator:
        chunk = chunk.decode()
        output += chunk
        chunk = chunk.split("\n", 1)
        if len(chunk) > 1:  # Indicates newline present
            full_line += chunk[0]
            logger.debug(strip_ansi(full_line).rstrip())
            full_line = ""
            if chunk[1]:
                full_line = chunk[1]
        else:
            full_line += chunk[0]
    if full_line:
        logger.debug(strip_ansi(full_line).rstrip())

    exit_code = api_client.exec_inspect(exec_handler["Id"]).get("ExitCode")
    return CommandResult(cmd, output, exit_code)
