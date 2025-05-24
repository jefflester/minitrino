"""Utility functions for Minitrino CLI tests."""

import json
import logging
import docker
import os
from typing import Dict, Optional

from click.testing import CliRunner, Result

from minitrino.cli import cli
from test.cli.constants import CLUSTER_NAME
from test.common import CommandResult, get_containers

logger = logging.getLogger("minitrino.test")


def cli_cmd(
    cmd: list[str],
    input: str | None = None,
    env: Optional[Dict[str, str]] = None,
    log_output: bool = True,
) -> Result:
    """
    Log and execute a CLI command.

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
        Whether to log the output of the command. Defaults to `True`.

    Returns
    -------
    Result
        The Click testing Result object.
    """
    msg = "Invoking CLI command '%s' %s"
    logger.info(msg % (cmd, " with input: %s" % input if input else ""))
    runner = CliRunner()
    env = env or {}
    result = runner.invoke(cli, cmd, input=input, env=env)
    if log_output:
        logger.info(f"Result output:\n{result.output}")
    return result


def docker_client() -> tuple[docker.DockerClient, docker.APIClient]:
    """Return a Docker client for test use."""
    from minitrino.core.docker.socket import resolve_docker_socket

    socket = resolve_docker_socket()
    logger.debug(f"Docker socket path: {socket}")
    return docker.DockerClient(base_url=socket), docker.APIClient(base_url=socket)


# ------------------------
# Config Helpers
# ------------------------


def update_metadata_json(module: str, updates: Optional[list[dict]] = None) -> None:
    """
    Update a given module's `metadata.json` file.

    Parameters
    ----------
    module : str
        The name of the module to update.
    updates : Optional[list[dict]]
        The list of dicts to update the module's metadata.json file
        with.
    """
    updates = updates or []
    path = get_metadata_json_path(module)
    with open(path, "r") as f:
        data = json.load(f)
    for update in updates:
        for k, v in update.items():
            data[k] = v
    with open(path, "w") as f:
        logger.debug(f"Updating {path} with {json.dumps(data)}")
        json.dump(data, f, indent=4)


# ------------------------
# Module Helpers
# ------------------------


def get_metadata_json_path(module: str) -> str:
    """Fetch the `metadata.json` file path for a given module."""
    metadata = get_module_metadata(module)
    return os.path.abspath(
        os.path.join(metadata[module]["module_dir"], "metadata.json")
    )


def get_module_metadata(module: str) -> dict:
    """Fetch metadata for a given module."""
    cmd = build_cmd("modules", append=["--module", module, "--json"], verbose=False)
    result = cli_cmd(cmd, log_output=False)
    return json.loads(normalize(result.output))


def get_module_yaml_path(module: str) -> str:
    """Fetch the path to a module's YAML file."""
    metadata = get_module_metadata(module)
    return os.path.abspath(metadata[module]["yaml_file"])


# ------------------------
# I/O Helpers
# ------------------------


def read_file(path: str) -> str:
    """Read a file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, contents: str, mode: str = "w") -> int:
    """
    Write content to a file at the given path.

    Parameters
    ----------
    path : str
        The path to the file to write to.
    contents : str
        The contents to write to the file.
    mode : str
        The mode to open the file in. Defaults to 'w'.
    """
    with open(path, mode, encoding="utf-8") as f:
        return f.write(contents)


# ------------------------
# Assertion Helpers
# ------------------------


def assert_exit_code(result: Result | CommandResult, expected: int = 0) -> None:
    """
    Assert the CLI result exit code matches expected.

    Parameters
    ----------
    result : Result or CommandResult
        The result to check.
    expected : int
        The expected exit code. Defaults to 0.
    """
    msg = "Unexpected exit code: %s (expected: %s). Output:\n%s" % (
        result.exit_code,
        expected,
        result.output,
    )
    assert result.exit_code == expected, msg


def assert_num_containers(expected: int = 0, all: bool = False) -> None:
    """
    Assert the expected number of existing containers.

    Parameters
    ----------
    expected : int
        The expected number of containers. Defaults to 0.
    all : bool
        Whether to count all containers or only running containers.
        Defaults to `False`.
    """
    containers = get_containers(all=all)
    container_names = [c.name for c in containers]
    msg = "Unexpected number of containers: %s (expected: %s) (containers: %s)" % (
        len(containers),
        expected,
        container_names,
    )
    assert len(containers) == expected, msg


def assert_containers_exist(*args: str, all: bool = False) -> None:
    """
    Assert the given containers exist.

    Parameters
    ----------
    args : tuple of str
        The names of the containers to assert exist.
    all : bool
        Whether to count all containers or only running containers.
        Defaults to `False`.
    """
    msg = "Expected container '%s' to exist but it does not."
    containers = get_containers(all=all)
    container_names = [c.name for c in containers]
    for name in args:
        assert name in container_names, msg % name


def assert_containers_not_exist(*args: str, all: bool = False) -> None:
    """
    Assert the given containers do not exist.

    Parameters
    ----------
    args : tuple of str
        The names of the containers to assert do not exist.
    all : bool
        Whether to count all containers or only running containers.
        Defaults to `False`.
    """
    msg = "Expected container '%s' to NOT exist but it does."
    containers = get_containers(all=all)
    container_names = [c.name for c in containers]
    for name in args:
        assert name not in container_names, msg % name


def assert_is_dir(path: str) -> None:
    """Assert the given path exists and is a directory."""
    assert os.path.exists(path), f"Path {path} does not exist."
    assert os.path.isdir(path), f"Path {path} is not a directory."


def assert_is_file(path: str) -> None:
    """Assert the given path exists and is a file."""
    assert os.path.exists(path), f"Path {path} does not exist."
    assert os.path.isfile(path), f"Path {path} is not a file."


def assert_in_file(*args: str, path: str) -> None:
    """
    Assert the given strings are in the file.

    Parameters
    ----------
    args : tuple of str
        The strings to assert are in the file.
    path : str
        The path to the file to check.
    """
    content = read_file(path)
    msg = "Expected string '%s' not found in file %s\nActual content:\n%s"
    for expected in args:
        assert expected in content, msg % (expected, path, content)


def assert_not_in_file(*args: str, path: str) -> None:
    """
    Assert the given strings are not in the file.

    Parameters
    ----------
    args : tuple of str
        The strings to assert are not in the file.
    path : str
        The path to the file to check.
    """
    content = read_file(path)
    msg = "Unexpected string '%s' found in file %s\nActual content:\n%s"
    for unexpected in args:
        assert unexpected not in content, msg % (unexpected, path, content)


def assert_in_output(*args: str, result: Result | CommandResult | list[str]) -> None:
    """
    Assert the given strings are in the result output.

    Parameters
    ----------
    args : tuple of str
        The strings to assert are in the result output.
    result : Result or CommandResult or list
        The result to check. Supports list[str] for testing log sinks.
    """
    msg = "Expected string '%s' not found in output:\n%s."
    if isinstance(result, list):
        joined = "\n".join(normalize(s) for s in result)
        for expected in args:
            assert expected in joined, msg % (expected, joined)
        return
    for expected in args:
        normalized = normalize(result.output)
        assert expected in normalized, msg % (expected, normalized)


def assert_not_in_output(*args: str, result: Result | CommandResult) -> None:
    """
    Assert the given strings are not in the result output.

    Parameters
    ----------
    args : tuple of str
        The strings to assert are not in the result output.
    result : Result or CommandResult
        The result to check.
    """
    msg = "Unexpected string '%s' found in output:\n%s."
    for unexpected in args:
        normalized = normalize(result.output)
        assert unexpected not in normalized, msg % (unexpected, normalized)


# ------------------------
# Fixture Helpers
# ------------------------


def shut_down() -> None:
    """Bring down all containers."""
    logger.debug("Bringing down all containers.")
    cli_cmd(build_cmd("down", "all", append=["--sig-kill"], verbose=False))


# ------------------------
# Scenario Helpers
# ------------------------


def get_scenario_ids(scenarios: list) -> list[str]:
    """Extract scenario IDs from test data."""
    return [getattr(sc, "id", str(sc)) for sc in scenarios]


def get_scenario_and_log_msg(scenarios: list) -> list[tuple]:
    """Return list of (scenario, log_msg) for parameterization."""
    return [(sc, getattr(sc, "log_msg", "")) for sc in scenarios]


# ------------------------
# String Helpers
# ------------------------


def normalize(s: str) -> str:
    """Normalize a string for assertions."""
    import re

    return re.sub(r"\s+", " ", s).strip()


def build_cmd(
    base: str,
    cluster: Optional[str] = CLUSTER_NAME,
    append: Optional[list[str]] = None,
    prepend: Optional[list[str]] = None,
    verbose: bool = True,
) -> list[str]:
    """
    Build a CLI command for CliRunner.

        [minitrino (<impl>)] [-v] [--cluster <cluster>] <prepend> <base>
        <append>

    Parameters
    ----------
    base : str
        The base command (e.g. 'down', 'remove').
    cluster : Optional[str]
        The cluster to use. Defaults to 'cli-test'.
    append : Optional[list[str]]
        Extra arguments to add to the command after the base command.
    prepend : Optional[list[str]]
        Extra arguments to add to the command before the base command.
    verbose : bool
        Whether to add the '-v' flag to the command. Defaults to `True`.

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
    cmd = ["--cluster", cluster, *prepend, base, *append]
    if verbose:
        cmd.insert(0, "-v")
    return cmd
