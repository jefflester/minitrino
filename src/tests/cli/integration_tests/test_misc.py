import os
from dataclasses import dataclass
from typing import Optional

import pytest

from tests import common
from tests.cli.integration_tests import utils
from tests.common import CONFIG_FILE

pytestmark = pytest.mark.usefixtures("log_test")
executor = common.MinitrinoExecutor(utils.CLUSTER_NAME)


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
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    cmd: dict
    input_val: Optional[str]
    expected_exit_code: int
    log_msg: str


daemon_off_scenarios = [
    DaemonOffScenario(
        id="down_daemon_off",
        cmd={"base": "down"},
        input_val=None,
        expected_exit_code=2,
        log_msg="Down command: fails when daemon is off",
    ),
    DaemonOffScenario(
        id="provision_daemon_off",
        cmd={"base": "provision"},
        input_val=None,
        expected_exit_code=2,
        log_msg="Provision command: fails when daemon is off",
    ),
    DaemonOffScenario(
        id="remove_daemon_off",
        cmd={"base": "remove"},
        input_val=None,
        expected_exit_code=2,
        log_msg="Remove command: fails when daemon is off",
    ),
    DaemonOffScenario(
        id="snapshot_daemon_off",
        cmd={"base": "snapshot", "append": ["--name", "test"]},
        input_val="y\n",
        expected_exit_code=2,
        log_msg="Snapshot command: fails when daemon is off",
    ),
    DaemonOffScenario(
        id="modules_daemon_off",
        cmd={"base": "modules", "append": ["--running"]},
        input_val=None,
        expected_exit_code=2,
        log_msg="Modules (running) command: fails when daemon is off",
    ),
]


@pytest.mark.flaky(
    reruns=0
)  # Disable retries - conflicts with session-scoped stop_docker
@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(daemon_off_scenarios),
    ids=utils.get_scenario_ids(daemon_off_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("stop_docker")
def test_daemon_off_scenarios(scenario: DaemonOffScenario) -> None:
    """Run each DaemonOffScenario."""
    err_msg = "Error when pinging the Docker server"
    result = executor.exec(executor.build_cmd(**scenario.cmd), scenario.input_val)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(err_msg, result=result)


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
@pytest.mark.usefixtures("cleanup_config")
def test_env_scenarios(scenario: EnvScenario) -> None:
    """Run each EnvScenario."""
    if scenario.source == "cli":
        result = executor.exec(
            executor.build_cmd(
                "modules",
                prepend=["--env", f"{scenario.envvar}={scenario.envval}"],
                debug=True,
            ),
        )
    elif scenario.source == "shell":
        result = executor.exec(
            executor.build_cmd("modules", debug=True),
            env={scenario.envvar: scenario.envval},
        )
    elif scenario.source == "config":
        utils.write_file(CONFIG_FILE, f"{scenario.envvar}={scenario.envval}", mode="a")
        result = executor.exec(executor.build_cmd("modules", debug=True))
        os.remove(CONFIG_FILE)
    else:  # unset
        result = executor.exec(executor.build_cmd("modules", debug=True))
    utils.assert_exit_code(result)
    if scenario.expected_present:
        utils.assert_in_output(scenario.envvar, scenario.envval, result=result)
    else:
        # For unset scenario, only check that the value doesn't appear
        # (the env var name may appear in module metadata)
        utils.assert_not_in_output(scenario.envval, result=result)


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
@pytest.mark.usefixtures("cleanup_config")
def test_invalid_env_scenarios(scenario: InvalidEnvScenario) -> None:
    """Run each InvalidEnvScenario."""
    result = executor.exec(
        executor.build_cmd("modules", prepend=["--env", scenario.envflag])
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
@pytest.mark.usefixtures("cleanup_config")
def test_invalid_lib_scenarios(scenario: InvalidLibScenario) -> None:
    """Run each InvalidLibScenario."""
    result = executor.exec(
        executor.build_cmd(
            "modules", prepend=["--env", f"LIB_PATH={scenario.lib_path}"]
        ),
    )
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(
        "This operation requires a library to be installed", result=result
    )


TEST_MULTI_ENV_MSG = "Pass in multiple environment variables"


@pytest.mark.usefixtures("cleanup_config")
@pytest.mark.parametrize("log_msg", [TEST_MULTI_ENV_MSG], indirect=True)
def test_multiple_env() -> None:
    """
    Verify that multiple environment variables can be successfully
    passed in.
    """
    result = executor.exec(
        executor.build_cmd(
            "modules",
            prepend=[
                "--env",
                "CLUSTER_VER=420-e",
                "--env",
                "FOO=bar",
            ],
            debug=True,
        ),
    )
    utils.assert_exit_code(result)
    utils.assert_in_output(
        "CLUSTER_VER",
        "420-e",
        "FOO",
        "bar",
        result=result,
    )
