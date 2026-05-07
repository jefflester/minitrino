"""Integration tests for the --source-code provisioning feature.

Requires the TRINO_SOURCE_PATH environment variable to point to a local Trino repository
with a completed Maven build (core/trino-server/target/). Tests are skipped when the
variable is not set.
"""

import os
import time
from dataclasses import dataclass

import pytest

from tests import common
from tests.cli.constants import CLUSTER_NAME, MINITRINO_CONTAINER
from tests.cli.integration_tests import utils

WORKER_CONTAINER = f"minitrino-worker-1-{CLUSTER_NAME}"
POSTGRES_CONTAINER = f"postgres-{CLUSTER_NAME}"

executor = common.MinitrinoExecutor(CLUSTER_NAME)

pytestmark = pytest.mark.usefixtures("log_test", "start_docker", "down")


@pytest.fixture(autouse=True, scope="module")
def clean_before_test():
    """Clean up the env before running tests."""
    utils.shut_down()
    executor.exec(
        executor.build_cmd("remove", "all", append=["--volume", "--network"]),
        log_output=False,
    )
    yield


@pytest.fixture()
def trino_source_path():
    """Return the Trino source path from environment, or skip."""
    path = os.environ.get("TRINO_SOURCE_PATH")
    if not path or not os.path.isdir(path):
        pytest.skip("TRINO_SOURCE_PATH not set or does not exist")
    return path


@dataclass
class SourceBuildScenario:
    """Source build provisioning scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    modules : list[str]
        Modules to provision.
    workers : int
        Number of workers to provision.
    expected_containers : int
        Expected number of running containers.
    expected_container_names : list[str]
        Container names to assert exist.
    verify_catalog : str
        If set, verify this catalog is available via SHOW CATALOGS.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    modules: list[str]
    workers: int
    expected_containers: int
    expected_container_names: list[str]
    verify_catalog: str
    log_msg: str


source_build_scenarios = [
    SourceBuildScenario(
        id="standalone",
        modules=[],
        workers=0,
        expected_containers=1,
        expected_container_names=[MINITRINO_CONTAINER],
        verify_catalog="",
        log_msg="Source build: standalone coordinator, no modules",
    ),
    SourceBuildScenario(
        id="module_and_worker",
        modules=["postgres"],
        workers=1,
        expected_containers=3,
        expected_container_names=[
            MINITRINO_CONTAINER,
            WORKER_CONTAINER,
            POSTGRES_CONTAINER,
        ],
        verify_catalog="postgres",
        log_msg="Source build: postgres module with one worker",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(source_build_scenarios),
    ids=utils.get_scenario_ids(source_build_scenarios),
    indirect=["log_msg"],
)
def test_source_build_scenarios(
    scenario: SourceBuildScenario, trino_source_path: str
) -> None:
    """Run each SourceBuildScenario."""
    append = ["--source-code", trino_source_path, "--image", "trino"]
    for module in scenario.modules:
        append.extend(["--module", module])
    if scenario.workers:
        append.extend(["--workers", str(scenario.workers)])

    result = executor.exec(executor.build_cmd(base="provision", append=append))
    utils.assert_exit_code(result, expected=0)

    utils.assert_num_containers(scenario.expected_containers)
    utils.assert_containers_exist(*scenario.expected_container_names)

    _wait_for_coordinator_ready(MINITRINO_CONTAINER)

    query_result = common.execute_in_coordinator(
        "trino-cli --execute 'SELECT 1'",
        MINITRINO_CONTAINER,
    )
    utils.assert_exit_code(query_result, expected=0)

    if scenario.verify_catalog:
        catalog_result = common.execute_in_coordinator(
            "trino-cli --execute 'SHOW CATALOGS'",
            MINITRINO_CONTAINER,
        )
        utils.assert_exit_code(catalog_result, expected=0)
        utils.assert_in_output(scenario.verify_catalog, result=catalog_result)


def _wait_for_coordinator_ready(container: str, timeout: int = 120) -> None:
    """Poll the Trino REST API until the coordinator reports started."""
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        if elapsed > timeout:
            raise TimeoutError(f"Coordinator did not become ready within {timeout}s")
        result = common.execute_cmd(
            "curl -sf http://localhost:8080/v1/info",
            container=container,
        )
        if result.exit_code == 0 and '"starting":false' in result.output:
            return
        time.sleep(1)
