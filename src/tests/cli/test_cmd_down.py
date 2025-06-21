from dataclasses import dataclass
from typing import Optional

import pytest

from tests import common
from tests.cli import utils
from tests.cli.constants import (
    CLUSTER_NAME,
    CLUSTER_NAME_2,
    MINITRINO_CONTAINER,
    REMOVED_CONTAINER_MSG,
    STOPPED_CONTAINER_MSG,
    TEST_CONTAINER,
)

pytestmark = pytest.mark.usefixtures(
    "log_test", "start_docker", "provision_clusters", "down"
)
builder = common.CLICommandBuilder(CLUSTER_NAME)


@dataclass
class DownScenario:
    """
    Down scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    provision : bool
        Whether to provision the environment before running the down
        command.
    down_args : list[str]
        Command line arguments to pass to the down command.
    expected_exit_code : int
        Expected exit code of the down command.
    expected_output : Optional[str | list[str]]
        Expected string(s) to be in the output of the down command.
    unexpected_output : Optional[str]
        Expected string to NOT be in the output of the down command.
    num_running : int
        Expected number of running containers.
    num_total : int
        Expected total number of containers (all=True).
    log_msg : str
        Log message to display before running the test.
    """

    id: str
    provision: bool
    down_args: list[str]
    expected_exit_code: int
    expected_output: Optional[str | list[str]]
    unexpected_output: Optional[str]
    num_running: int
    num_total: int
    log_msg: str


down_scenarios = [
    DownScenario(
        id="no_containers",
        provision=False,
        down_args=[],
        expected_exit_code=0,
        expected_output="No containers to bring down",
        unexpected_output=None,
        num_running=0,
        num_total=0,
        log_msg="Down: no containers to bring down",
    ),
    DownScenario(
        id="running",
        provision=True,
        down_args=[],
        expected_exit_code=0,
        expected_output=[STOPPED_CONTAINER_MSG, REMOVED_CONTAINER_MSG],
        unexpected_output=None,
        num_running=0,
        num_total=0,
        log_msg="Down: bring down running containers",
    ),
    DownScenario(
        id="running_sigkill",
        provision=True,
        down_args=["--sig-kill"],
        expected_exit_code=0,
        expected_output=[STOPPED_CONTAINER_MSG, REMOVED_CONTAINER_MSG],
        unexpected_output=None,
        num_running=0,
        num_total=0,
        log_msg="Down: bring down running containers with --sig-kill",
    ),
    DownScenario(
        id="keep",
        provision=True,
        down_args=["--keep"],
        expected_exit_code=0,
        expected_output=STOPPED_CONTAINER_MSG,
        unexpected_output=REMOVED_CONTAINER_MSG,
        num_running=0,
        num_total=2,
        log_msg="Down: keep containers with --keep",
    ),
    DownScenario(
        id="keep_sigkill",
        provision=True,
        down_args=["--keep", "--sig-kill"],
        expected_exit_code=0,
        expected_output=STOPPED_CONTAINER_MSG,
        unexpected_output=REMOVED_CONTAINER_MSG,
        num_running=0,
        num_total=2,
        log_msg="Down: keep containers with --keep and --sig-kill",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(down_scenarios),
    ids=utils.get_scenario_ids(down_scenarios),
    indirect=["log_msg"],
)
def test_down_scenarios(scenario: DownScenario) -> None:
    """Run each DownScenario."""
    if scenario.provision:
        common.cli_cmd(builder.build_cmd(base="provision", append=["--module", "test"]))
    cmd = builder.build_cmd(base="down", append=scenario.down_args)
    result = common.cli_cmd(cmd)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    if scenario.expected_output:
        if isinstance(scenario.expected_output, list):
            utils.assert_in_output(*scenario.expected_output, result=result)
        else:
            utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.unexpected_output:
        utils.assert_not_in_output(scenario.unexpected_output, result=result)
    utils.assert_num_containers(scenario.num_running)
    utils.assert_num_containers(scenario.num_total, all=True)


CLUSTER_NAME_MSG = "Testing --cluster flag with cluster name 'test'"


@pytest.mark.parametrize(
    ("log_msg", "provision_clusters"),
    [(CLUSTER_NAME_MSG, {"cluster_names": [CLUSTER_NAME_2], "keepalive": True})],
    indirect=True,
)
def test_cluster() -> None:
    """Verify `--cluster ${name}` works as expected."""
    cmd = builder.build_cmd(base="down", cluster=CLUSTER_NAME, append=["--sig-kill"])
    result = common.cli_cmd(cmd)
    utils.assert_exit_code(result)
    utils.assert_in_output(STOPPED_CONTAINER_MSG, REMOVED_CONTAINER_MSG, result=result)
    utils.assert_num_containers(2, all=True)

    cmd2 = builder.build_cmd(base="down", cluster=CLUSTER_NAME_2, append=["--sig-kill"])
    result = common.cli_cmd(cmd2)
    utils.assert_exit_code(result)
    utils.assert_in_output(STOPPED_CONTAINER_MSG, REMOVED_CONTAINER_MSG, result=result)
    utils.assert_num_containers(0, all=True)


CLUSTER_KEEP_MSG = "Testing --cluster flag with --keep and --sig-kill flags"


@pytest.mark.parametrize(
    ("log_msg", "provision_clusters"),
    [(CLUSTER_KEEP_MSG, {"cluster_names": [CLUSTER_NAME_2], "keepalive": True})],
    indirect=True,
)
def test_cluster_keep() -> None:
    """Verify `--cluster ${name}` works as expected with the `--keep`
    flag."""
    append = ["--sig-kill", "--keep"]
    cmd = builder.build_cmd(base="down", cluster=CLUSTER_NAME, append=append)
    result = common.cli_cmd(cmd)
    utils.assert_exit_code(result)
    utils.assert_in_output(STOPPED_CONTAINER_MSG, result=result)
    utils.assert_not_in_output(REMOVED_CONTAINER_MSG, result=result)
    utils.assert_num_containers(4, all=True)
    utils.assert_containers_exist(MINITRINO_CONTAINER, TEST_CONTAINER, all=True)

    cmd2 = builder.build_cmd(base="down", cluster=CLUSTER_NAME_2, append=append)
    result = common.cli_cmd(cmd2)
    utils.assert_exit_code(result)
    utils.assert_in_output(STOPPED_CONTAINER_MSG, result=result)
    utils.assert_not_in_output(REMOVED_CONTAINER_MSG, result=result)
    utils.assert_num_containers(0)
    utils.assert_num_containers(4, all=True)
    utils.assert_containers_exist(MINITRINO_CONTAINER, TEST_CONTAINER, all=True)
