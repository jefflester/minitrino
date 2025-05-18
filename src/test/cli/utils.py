"""Utility functions for Minitrino CLI tests."""

import os
import json

from logging import Logger
from typing import Optional, Dict
from click.testing import CliRunner, Result

from minitrino.cli import cli
from test.common import CommandResult, get_containers
from test.cli.constants import CLUSTER_NAME


def cli_cmd(
    cmd: list[str],
    logger: Logger = None,
    input: str | None = None,
    env: Optional[Dict[str, str]] = None,
) -> Result:
    """
    Log and execute a CLI command.

    Parameters
    ----------
    cmd : list[str]
        The command and arguments to invoke.
    logger : Logger
        Logger to use for logging the invocation. If None, no log is produced.
    input : str | None
        Input string to pass to the command (for prompts, etc.). Defaults to None.
    env : Optional[Dict[str, str]]
        Environment variables to set for the command. Defaults to an empty dict.

    Returns
    -------
    Result
        The Click testing Result object.
    """
    if logger:
        msg = "Invoking CLI command '%s' %s"
        logger.info(msg % (cmd, " with input: %s" % input if input else ""))
    runner = CliRunner()
    env = env or {}
    result = runner.invoke(cli, cmd, input=input, env=env)
    logger.debug(f"Result output: {result.output}")
    return result


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
        The list of dicts to update the module's metadata.json file with.
    """
    updates = updates or []
    path = get_metadata_json_path(module)
    with open(path, "r") as f:
        data = json.load(f)
    for update in updates:
        for k, v in update.items():
            data[k] = v
    with open(path, "w") as f:
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
    result = cli_cmd(build_cmd("modules", append=["--module", module, "--json"]))
    return json.loads(clean_str(result.output))


def get_module_yaml_path(module: str) -> str:
    """Fetch the path to a module's YAML file."""
    metadata = get_module_metadata(module)
    return os.path.abspath(metadata[module]["yaml_file"])


# ------------------------
# File Helpers
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
    msg = "Unexpected exit code: %s (expected: %s)\nOutput: %s" % (
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
        Whether to count all containers or only running containers. Defaults to `False`.
    """
    containers = get_containers(all=all)
    msg = "Unexpected number of containers: %s (expected: %s)" % (
        len(containers),
        expected,
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
        Whether to count all containers or only running containers. Defaults to `False`.
    """
    msg = "Container %s does not exist."
    for name in args:
        assert name in get_containers(name, all=all), msg % name


def assert_containers_not_exist(*args: str, all: bool = False) -> None:
    """
    Assert the given containers do not exist.

    Parameters
    ----------
    args : tuple of str
        The names of the containers to assert do not exist.
    all : bool
        Whether to count all containers or only running containers. Defaults to `False`.
    """
    msg = "Container %s exists."
    for name in args:
        assert name not in get_containers(name, all=all), msg % name


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
    for expected in args:
        assert expected in content, f"Expected string not found in file: {expected}"


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
    msg = "Unexpected string %s found in file."
    for unexpected in args:
        assert unexpected not in content, msg % unexpected


def assert_in_output(*args: str, result: Result | CommandResult) -> None:
    """
    Assert the given strings are in the result output.

    Parameters
    ----------
    args : tuple of str
        The strings to assert are in the result output.
    result : Result or CommandResult
        The result to check.
    """
    msg = "Expected string %s not found in output."
    for expected in args:
        assert expected in clean_str(result.output), msg % expected


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
    msg = "Unexpected string %s found in output."
    for unexpected in args:
        assert unexpected not in clean_str(result.output), msg % unexpected


# ------------------------
# Fixture Helpers
# ------------------------


def shut_down() -> None:
    """Bring down all containers."""
    cli_cmd(build_cmd("down", "all", append=["--sig-kill"]))


# ------------------------
# Scenario Helpers
# ------------------------


def get_scenario_ids(scenarios: list) -> list[str]:
    """Extract scenario IDs from test data."""
    return [getattr(sc, "id", str(sc)) for sc in scenarios]


# ------------------------
# String Helpers
# ------------------------


def clean_str(s: str) -> str:
    """Remove unwanted characters from a string."""
    return s.replace("\n", "").replace(" ", "")


def build_cmd(
    base: str,
    cluster: Optional[str] = CLUSTER_NAME,
    append: Optional[list[str]] = None,
    prepend: Optional[list[str]] = None,
) -> list[str]:
    """
    Build a CLI command for CliRunner.

        [minitrino (<impl>)] [-v] [--cluster <cluster>] <prepend> <base> <append>

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
    cmd = ["-v", "--cluster", cluster, *prepend, base, *append]
    return cmd
