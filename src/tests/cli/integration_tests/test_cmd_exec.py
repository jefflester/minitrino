from dataclasses import dataclass

import pytest

from tests import common
from tests.cli.constants import CLUSTER_NAME
from tests.cli.integration_tests import utils

pytestmark = pytest.mark.usefixtures("log_test", "start_docker")
executor = common.MinitrinoExecutor(CLUSTER_NAME)


@dataclass
class ExecScenario:
    """
    Exec scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    cmd_flags : Optional[list[str]]
        The command flags to use.
    cmd : str
        The command to run.
    expected_exit_code : int
        The expected exit code.
    expected_output : list[str]
        The expected output strings to assert.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    cmd_flags: list[str]
    cmd: str
    expected_exit_code: int
    expected_output: list[str]
    log_msg: str


exec_scenarios = [
    ExecScenario(
        id="exec_coordinator",
        cmd_flags=[],
        cmd="bash -c 'ls /etc/${CLUSTER_DIST}/'",
        expected_exit_code=0,
        expected_output=["config.properties", "log.properties"],
        log_msg="Run exec in coordinator - should succeed",
    ),
    ExecScenario(
        id="exec_coordinator_fail",
        cmd_flags=[],
        cmd="ls /foo/bar",
        expected_exit_code=1,
        expected_output=["No such file or directory"],
        log_msg="Run exec in coordinator - should fail",
    ),
    ExecScenario(
        id="exec_test_container",
        cmd_flags=["--container", "test"],
        cmd="ls /etc/",
        expected_exit_code=0,
        expected_output=["init.d", "profile.d"],
        log_msg="Run exec in test container",
    ),
    ExecScenario(
        id="exec_invalid_container",
        cmd_flags=["--container", "foo"],
        cmd="ls /etc/",
        expected_exit_code=2,
        expected_output=["not found"],
        log_msg="Run exec in invalid container",
    ),
    ExecScenario(
        id="exec_invalid_command",
        cmd_flags=[],
        cmd="foo",
        expected_exit_code=1,
        expected_output=["executable file not found"],
        log_msg="Run exec with invalid command",
    ),
    ExecScenario(
        id="exec_cluster_name_provided",
        cmd_flags=["--container", f"minitrino-{CLUSTER_NAME}"],
        cmd="bash -c 'ls /etc/${CLUSTER_DIST}/'",
        expected_exit_code=0,
        expected_output=["config.properties", "log.properties"],
        log_msg="Run exec with cluster name appended to container name",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(exec_scenarios),
    ids=utils.get_scenario_ids(exec_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.parametrize(
    "provision_clusters",
    [{"keepalive": True}],
    indirect=True,
)
@pytest.mark.usefixtures("provision_clusters", "remove")
def test_exec_scenarios(scenario: ExecScenario) -> None:
    """Run each ExecScenario."""
    append_flags = []
    if scenario.cmd_flags:
        append_flags.extend(scenario.cmd_flags)
    append_flags.append(scenario.cmd)
    cmd = executor.build_cmd(base="exec", append=append_flags)
    result = executor.exec(cmd)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(*scenario.expected_output, result=result)
