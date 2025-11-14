from dataclasses import dataclass
from typing import Any

import pytest

from tests import common
from tests.cli.constants import CLUSTER_NAME, CLUSTER_NAME_2
from tests.cli.integration_tests import utils

CMD_RESOURCES: utils.BuildCmdArgs = {"base": "resources", "cluster": "all"}
CLUSTER_RESOURCES = [
    f"minitrino_{CLUSTER_NAME}",  # network
    f"minitrino-{CLUSTER_NAME}_test-data",  # volume
    f"minitrino-{CLUSTER_NAME}",  # container
    f"test-{CLUSTER_NAME}",  # container
    r"localhost:808[0-9]",  # host endpoint
    r"8080:808[0-9]",  # port
]
CLUSTER_2_RESOURCES = [
    f"minitrino_{CLUSTER_NAME_2}",  # network
    f"minitrino-{CLUSTER_NAME_2}_test-data",  # volume
    f"minitrino-{CLUSTER_NAME_2}",  # container
    f"test-{CLUSTER_NAME_2}",  # container
    r"localhost:808[0-9]",  # host endpoint
    r"8080:808[0-9]",  # port
]

pytestmark = pytest.mark.usefixtures(
    "log_test", "start_docker", "remove", "provision_clusters"
)
executor = common.MinitrinoExecutor(utils.CLUSTER_NAME)


@dataclass
class ResourcesScenario:
    """Resources scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    provision_data : dict[str, Any]
        Data to pass to the provision_clusters fixture.
    cluster_count : int
        Number of clusters to provision.
    log_msg : str
        Log message to display before running the test.
    """

    id: str
    provision_data: dict[str, Any]
    cluster_count: int
    log_msg: str


resources_scenarios = [
    ResourcesScenario(
        id="resources_one_cluster",
        provision_data={"keepalive": True},
        cluster_count=1,
        log_msg="Resources for one cluster",
    ),
    ResourcesScenario(
        id="resources_two_clusters",
        provision_data={"cluster_names": [CLUSTER_NAME_2], "keepalive": True},
        cluster_count=2,
        log_msg="Resources for two clusters",
    ),
    ResourcesScenario(
        id="resources_zero_clusters",
        provision_data={"keepalive": False},
        cluster_count=0,
        log_msg="Resources for zero clusters",
    ),
    ResourcesScenario(
        id="resources_stopped_cluster",
        provision_data={"keepalive": True},
        cluster_count=1,
        log_msg="Resources for stopped cluster",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg,provision_clusters",
    [
        (sc, getattr(sc, "log_msg", ""), getattr(sc, "provision_data", {}))
        for sc in resources_scenarios
    ],
    ids=utils.get_scenario_ids(resources_scenarios),
    indirect=["log_msg", "provision_clusters"],
)
def test_resources_scenarios(scenario: ResourcesScenario) -> None:
    """Run each ResourcesScenario."""
    if scenario.cluster_count == 0:
        executor.exec(
            executor.build_cmd("remove", "all", append=["--volumes", "--networks"])
        )
        cmd_args = CMD_RESOURCES.copy()
        result = executor.exec(executor.build_cmd(**cmd_args))
        utils.assert_exit_code(result)
        utils.assert_not_in_output(*CLUSTER_RESOURCES, result=result)
    cmd_args = CMD_RESOURCES.copy()
    result = executor.exec(executor.build_cmd(**cmd_args))
    utils.assert_exit_code(result)
    if scenario.cluster_count == 1:
        utils.assert_in_output(*CLUSTER_RESOURCES, result=result)
    if scenario.cluster_count == 2:
        utils.assert_in_output(*CLUSTER_RESOURCES, *CLUSTER_2_RESOURCES, result=result)
