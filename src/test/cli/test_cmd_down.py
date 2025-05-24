from dataclasses import dataclass
from typing import Optional

import pytest

from test.cli import utils
from test.cli.constants import (
    CLUSTER_NAME,
    CLUSTER_NAME_2,
    MINITRINO_CONTAINER,
    REMOVED_CONTAINER_MSG,
    STOPPED_CONTAINER_MSG,
    TEST_CONTAINER,
)

CMD_DOWN = {"base": "down"}
CMD_PROVISION = {"base": "provision", "append": ["--module", "test"]}

pytestmark = pytest.mark.usefixtures("start_docker")


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
    expected_in_output : Optional[str | list[str]]
        Expected string(s) to be in the output of the down command.
    expected_not_in_output : Optional[str]
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
    expected_in_output: Optional[str | list[str]]
    expected_not_in_output: Optional[str]
    num_running: int
    num_total: int
    log_msg: str


down_scenarios = [
    DownScenario(
        id="no_containers",
        provision=False,
        down_args=[],
        expected_exit_code=0,
        expected_in_output="No containers to bring down",
        expected_not_in_output=None,
        num_running=0,
        num_total=0,
        log_msg="Down: no containers to bring down",
    ),
    DownScenario(
        id="running",
        provision=True,
        down_args=[],
        expected_exit_code=0,
        expected_in_output=[STOPPED_CONTAINER_MSG, REMOVED_CONTAINER_MSG],
        expected_not_in_output=None,
        num_running=0,
        num_total=0,
        log_msg="Down: bring down running containers",
    ),
    DownScenario(
        id="running_sigkill",
        provision=True,
        down_args=["--sig-kill"],
        expected_exit_code=0,
        expected_in_output=[STOPPED_CONTAINER_MSG, REMOVED_CONTAINER_MSG],
        expected_not_in_output=None,
        num_running=0,
        num_total=0,
        log_msg="Down: bring down running containers with --sig-kill",
    ),
    DownScenario(
        id="keep",
        provision=True,
        down_args=["--keep"],
        expected_exit_code=0,
        expected_in_output=STOPPED_CONTAINER_MSG,
        expected_not_in_output=REMOVED_CONTAINER_MSG,
        num_running=0,
        num_total=2,
        log_msg="Down: keep containers with --keep",
    ),
    DownScenario(
        id="keep_sigkill",
        provision=True,
        down_args=["--keep", "--sig-kill"],
        expected_exit_code=0,
        expected_in_output=STOPPED_CONTAINER_MSG,
        expected_not_in_output=REMOVED_CONTAINER_MSG,
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
@pytest.mark.usefixtures("log_test", "down")
def test_down_scenarios(scenario: DownScenario) -> None:
    """Run each DownScenario."""
    if scenario.provision:
        utils.cli_cmd(utils.build_cmd(**CMD_PROVISION))
    cmd = utils.build_cmd(**CMD_DOWN, append=scenario.down_args)
    result = utils.cli_cmd(cmd)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    if scenario.expected_in_output:
        if isinstance(scenario.expected_in_output, list):
            utils.assert_in_output(*scenario.expected_in_output, result=result)
        else:
            utils.assert_in_output(scenario.expected_in_output, result=result)
    if scenario.expected_not_in_output:
        utils.assert_not_in_output(scenario.expected_not_in_output, result=result)
    utils.assert_num_containers(scenario.num_running)
    utils.assert_num_containers(scenario.num_total, all=True)


CLUSTER_NAME_MSG = "Testing --cluster flag with cluster name 'test'"


@pytest.mark.parametrize(
    ("log_msg", "provision_clusters"),
    [(CLUSTER_NAME_MSG, {"cluster_names": [CLUSTER_NAME_2], "keepalive": True})],
    indirect=True,
)
@pytest.mark.usefixtures("log_test", "provision_clusters", "down")
def test_cluster() -> None:
    """Verify `--cluster ${name}` works as expected."""
    cmd = utils.build_cmd(**CMD_DOWN, cluster=CLUSTER_NAME, append=["--sig-kill"])
    result = utils.cli_cmd(cmd)
    utils.assert_exit_code(result)
    utils.assert_in_output(STOPPED_CONTAINER_MSG, REMOVED_CONTAINER_MSG, result=result)
    utils.assert_num_containers(2, all=True)

    cmd2 = utils.build_cmd(**CMD_DOWN, cluster=CLUSTER_NAME_2, append=["--sig-kill"])
    result = utils.cli_cmd(cmd2)
    utils.assert_exit_code(result)
    utils.assert_in_output(STOPPED_CONTAINER_MSG, REMOVED_CONTAINER_MSG, result=result)
    utils.assert_num_containers(0, all=True)


CLUSTER_KEEP_MSG = "Testing --cluster flag with --keep and --sig-kill flags"


@pytest.mark.parametrize(
    ("log_msg", "provision_clusters"),
    [(CLUSTER_KEEP_MSG, {"cluster_names": [CLUSTER_NAME_2], "keepalive": True})],
    indirect=True,
)
@pytest.mark.usefixtures("log_test", "provision_clusters", "down")
def test_cluster_keep() -> None:
    """Verify `--cluster ${name}` works as expected with the `--keep`
    flag."""
    append = ["--sig-kill", "--keep"]
    cmd = utils.build_cmd(**CMD_DOWN, cluster=CLUSTER_NAME, append=append)
    result = utils.cli_cmd(cmd)
    utils.assert_exit_code(result)
    utils.assert_in_output(STOPPED_CONTAINER_MSG, result=result)
    utils.assert_not_in_output(REMOVED_CONTAINER_MSG, result=result)
    utils.assert_num_containers(4, all=True)
    utils.assert_containers_exist(MINITRINO_CONTAINER, TEST_CONTAINER, all=True)

    cmd2 = utils.build_cmd(**CMD_DOWN, cluster=CLUSTER_NAME_2, append=append)
    result = utils.cli_cmd(cmd2)
    utils.assert_exit_code(result)
    utils.assert_in_output(STOPPED_CONTAINER_MSG, result=result)
    utils.assert_not_in_output(REMOVED_CONTAINER_MSG, result=result)
    utils.assert_num_containers(0)
    utils.assert_num_containers(4, all=True)
    utils.assert_containers_exist(MINITRINO_CONTAINER, TEST_CONTAINER, all=True)
