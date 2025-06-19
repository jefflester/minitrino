from dataclasses import dataclass
from importlib.metadata import version
from typing import List

import pytest

from tests import common
from tests.cli import utils


@dataclass
class VersionScenario:
    """
    Scenario for testing the version command.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    prepend : list[str]
        List of CLI args to prepend (e.g., -e ...).
    append : list[str]
        List of CLI args to append (e.g., --version).
    expected_output : list[str]
        List of strings expected in the output.
    unexpected_output : list[str]
        List of strings NOT expected in the output.
    expected_exit_code : int
        Expected exit code (default 0).
    log_msg : str
        Log message for the scenario.
    """

    id: str
    prepend: List[str]
    append: List[str]
    expected_output: List[str]
    unexpected_output: List[str]
    log_msg: str
    expected_exit_code: int = 0


NOT_INSTALLED = "NOT INSTALLED"
CLI_VERSION = version("Minitrino")

version_scenarios = [
    VersionScenario(
        id="plain_version",
        prepend=[],
        append=["--version"],
        expected_output=[CLI_VERSION],
        unexpected_output=[NOT_INSTALLED],
        log_msg="Basic --version outputs CLI version",
    ),
    VersionScenario(
        id="invalid_env",
        prepend=["--env", "akdfhajkdfhkw"],
        append=["--version"],
        expected_output=["Invalid key-value pair"],
        unexpected_output=[NOT_INSTALLED],
        expected_exit_code=2,
        log_msg="Fails on invalid env",
    ),
    VersionScenario(
        id="multiple_envs",
        prepend=["--env", "foo=bar", "-e", "baz=qux"],
        append=["--version"],
        expected_output=[CLI_VERSION],
        unexpected_output=[NOT_INSTALLED],
        log_msg="Multiple --env flags still print version",
    ),
    VersionScenario(
        id="invalid_lib_path",
        prepend=["--env", "lib_path=/foo/bar/baz"],
        append=["--version"],
        expected_output=[CLI_VERSION, NOT_INSTALLED],
        unexpected_output=[],
        log_msg="Invalid lib path - show CLI version, not lib version",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(version_scenarios),
    ids=utils.get_scenario_ids(version_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("log_test")
def test_version_scenarios(scenario: VersionScenario) -> None:
    """Test various version command scenarios."""
    # Execute these tests directly in the shell since sys.argv doesn't
    # get passed through Click.testing.CliRunner, and we need those to
    # resolve env flags for early eval in the CLI.
    cmd = utils.build_cmd(prepend=scenario.prepend, append=scenario.append)
    cmd.insert(0, "minitrino")
    result = common.execute_cmd(" ".join(cmd))
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(*scenario.expected_output, result=result)
    utils.assert_not_in_output(*scenario.unexpected_output, result=result)
