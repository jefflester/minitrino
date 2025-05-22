import os
from dataclasses import dataclass
from typing import Optional

import pytest

from test.cli import utils
from test.common import CONFIG_FILE


@dataclass
class DaemonOffScenario:
    """
    Daemon off scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    cmd : dict
        The command to run.
    input_val : Optional[str]
        The input value.
    expected_exit_code : int
        The expected exit code.
    expected_in_output : str
        The expected output string to assert.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    cmd: dict
    input_val: Optional[str]
    expected_exit_code: int
    expected_in_output: str
    log_msg: str


daemon_off_scenarios = [
    DaemonOffScenario(
        id="down_daemon_off",
        cmd={"base": "down"},
        input_val=None,
        expected_exit_code=2,
        expected_in_output="Error when pinging the Docker server",
        log_msg="Down command: fails when daemon is off",
    ),
    DaemonOffScenario(
        id="provision_daemon_off",
        cmd={"base": "provision"},
        input_val=None,
        expected_exit_code=2,
        expected_in_output="Error when pinging the Docker server",
        log_msg="Provision command: fails when daemon is off",
    ),
    DaemonOffScenario(
        id="remove_daemon_off",
        cmd={"base": "remove"},
        input_val=None,
        expected_exit_code=2,
        expected_in_output="Error when pinging the Docker server",
        log_msg="Remove command: fails when daemon is off",
    ),
    DaemonOffScenario(
        id="snapshot_daemon_off",
        cmd={"base": "snapshot", "append": ["--name", "test"]},
        input_val="y\n",
        expected_exit_code=2,
        expected_in_output="Error when pinging the Docker server",
        log_msg="Snapshot command: fails when daemon is off",
    ),
    DaemonOffScenario(
        id="modules_daemon_off",
        cmd={"base": "modules", "append": ["--running"]},
        input_val=None,
        expected_exit_code=2,
        expected_in_output="Error when pinging the Docker server",
        log_msg="Modules (running) command: fails when daemon is off",
    ),
]


@pytest.mark.parametrize(
    "scenario",
    daemon_off_scenarios,
    ids=utils.get_scenario_ids(daemon_off_scenarios),
    indirect=False,
)
@pytest.mark.usefixtures("log_test", "stop_docker")
def test_daemon_off_scenarios(scenario: DaemonOffScenario) -> None:
    """Run each DaemonOffScenario."""
    result = utils.cli_cmd(utils.build_cmd(**scenario.cmd), scenario.input_val)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(scenario.expected_in_output, result=result)


@dataclass
class EnvScenario:
    """
    Env scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    envvar : str
        The environment variable to set.
    envval : str
        The value of the environment variable.
    source : str
        The source of the environment variable.
    expected_present : bool
        Whether the environment variable is expected to be present.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    envvar: str
    envval: str
    source: str
    expected_present: bool
    log_msg: str


env_scenarios = [
    EnvScenario(
        id="env_from_cli",
        envvar="CONFIG_PROPERTIES",
        envval="query.max-memory=1PB",
        source="cli",
        expected_present=True,
        log_msg="Env passed from CLI - should be set",
    ),
    EnvScenario(
        id="env_from_shell",
        envvar="CONFIG_PROPERTIES",
        envval="query.max-memory=1PB",
        source="shell",
        expected_present=True,
        log_msg="Env passed from shell - should be set",
    ),
    EnvScenario(
        id="env_from_config",
        envvar="CONFIG_PROPERTIES",
        envval="query.max-memory=1PB",
        source="config",
        expected_present=True,
        log_msg="Env passed from config - should be set",
    ),
    EnvScenario(
        id="env_unset",
        envvar="CONFIG_PROPERTIES",
        envval="query.max-memory=1PB",
        source="unset",
        expected_present=False,
        log_msg="Env unset - should not be set",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(env_scenarios),
    ids=utils.get_scenario_ids(env_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("log_test", "cleanup_config")
def test_env_scenarios(scenario: EnvScenario) -> None:
    """Run each EnvScenario."""
    if scenario.source == "cli":
        result = utils.cli_cmd(
            utils.build_cmd(
                "version", prepend=["--env", f"{scenario.envvar}={scenario.envval}"]
            ),
        )
    elif scenario.source == "shell":
        result = utils.cli_cmd(
            utils.build_cmd("version"),
            env={scenario.envvar: scenario.envval},
        )
    elif scenario.source == "config":
        utils.write_file(CONFIG_FILE, f"{scenario.envvar}={scenario.envval}", mode="a")
        result = utils.cli_cmd(utils.build_cmd("version"))
        os.remove(CONFIG_FILE)
    else:  # unset
        result = utils.cli_cmd(utils.build_cmd("version"))
    utils.assert_exit_code(result)
    if scenario.expected_present:
        utils.assert_in_output(scenario.envvar, scenario.envval, result=result)
    else:
        utils.assert_not_in_output(scenario.envvar, scenario.envval, result=result)


@dataclass
class InvalidEnvScenario:
    """
    Invalid environment variable scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    envflag : str
        The environment variable flag.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    envflag: str
    log_msg: str


invalid_env_scenarios = [
    InvalidEnvScenario(
        id="missing_equals",
        envflag="COMPOSE_PROJECT_NAMEtest",
        log_msg="Env var missing equals - should error",
    ),
    InvalidEnvScenario(
        id="empty_key_value",
        envflag="=",
        log_msg="Env var empty key - should error",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(invalid_env_scenarios),
    ids=utils.get_scenario_ids(invalid_env_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("log_test", "cleanup_config")
def test_invalid_env_scenarios(scenario: InvalidEnvScenario) -> None:
    """Run each InvalidEnvScenario."""
    result = utils.cli_cmd(
        utils.build_cmd("version", prepend=["--env", scenario.envflag])
    )
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output("Invalid key-value pair", result=result)


@dataclass
class InvalidLibScenario:
    """
    Invalid library scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    lib_path : str
        The library path to test.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    lib_path: str
    log_msg: str


invalid_lib_scenarios = [
    InvalidLibScenario(
        id="nonexistent_dir",
        lib_path="/_foo_bar/",
        log_msg="Point lib path to nonexistent directory",
    ),
    InvalidLibScenario(
        id="real_dir_not_library",
        lib_path="/tmp/",
        log_msg="Point library to real directory that is not a valid library",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(invalid_lib_scenarios),
    ids=utils.get_scenario_ids(invalid_lib_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("log_test", "cleanup_config")
def test_invalid_lib_scenarios(scenario: InvalidLibScenario) -> None:
    """Run each InvalidLibScenario."""
    result = utils.cli_cmd(
        utils.build_cmd("modules", prepend=["--env", f"LIB_PATH={scenario.lib_path}"]),
    )
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(
        "This operation requires a library to be installed", result=result
    )


TEST_MULTI_ENV_MSG = "Pass in multiple environment variables"


@pytest.mark.usefixtures("log_test", "cleanup_config")
@pytest.mark.parametrize("log_msg", [TEST_MULTI_ENV_MSG], indirect=True)
def test_multiple_env() -> None:
    """
    Verify that multiple environment variables can be successfully
    passed in.
    """
    result = utils.cli_cmd(
        utils.build_cmd(
            "version",
            prepend=[
                "--env",
                "COMPOSE_PROJECT_NAME=test",
                "--env",
                "CLUSTER_VER=420-e",
                "--env",
                "TRINO=is=awesome",
            ],
        ),
    )
    utils.assert_exit_code(result)
    utils.assert_in_output(
        '"COMPOSE_PROJECT_NAME": "test"',
        '"CLUSTER_VER": "420-e"',
        '"TRINO": "is=awesome"',
        result=result,
    )
