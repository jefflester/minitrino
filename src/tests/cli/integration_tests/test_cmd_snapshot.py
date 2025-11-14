import copy
import os
import shutil
from dataclasses import dataclass
from typing import Generator, Optional

import pytest
from click.testing import Result

from minitrino.settings import SCRUBBED
from tests import common
from tests.cli.integration_tests import utils
from tests.common import MINITRINO_USER_DIR

SNAPSHOT_NAME = "test"

CMD_SNAPSHOT: utils.BuildCmdArgs = {"base": "snapshot"}
CMD_SNAPSHOT_TEST: utils.BuildCmdArgs = {
    "base": "snapshot",
    "append": ["--name", SNAPSHOT_NAME],
}

SNAPSHOT_DIR = os.path.join(MINITRINO_USER_DIR, "snapshots")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, f"{SNAPSHOT_NAME}.tar.gz")
MINITRINO_USER_SNAPSHOTS_DIR = os.path.join(MINITRINO_USER_DIR, "snapshots")

executor = common.MinitrinoExecutor(utils.CLUSTER_NAME)


@pytest.fixture
def cleanup_snapshot(request: pytest.FixtureRequest) -> Generator:
    """
    Removes the snapshot directory before and after the test.
    """

    def _rm():
        shutil.rmtree(MINITRINO_USER_SNAPSHOTS_DIR, ignore_errors=True)

    if getattr(request, "param", False):
        yield
    else:
        _rm()
        yield
        _rm()


pytestmark = pytest.mark.usefixtures(
    "log_test", "start_docker", "remove", "cleanup_snapshot"
)


@dataclass
class SnapshotScenario:
    """
    Snapshot scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    append_flags : list[str]
        Flags to append to the command.
    check_yaml : bool
        Whether to check the YAML file.
    expected_output : Optional[str]
        Expected output.
    expected_in_file : Optional[str | list[str]]
        Expected content in file.
    expected_not_in_file : Optional[str | list[str]]
        Expected content NOT in file.
    keepalive : bool
        Whether to keep the cluster alive.
    log_msg : str
        Log message.
    """

    id: str
    append_flags: list[str]
    check_yaml: bool
    expected_output: Optional[str]
    expected_in_file: Optional[str | list[str]]
    expected_not_in_file: Optional[str | list[str]]
    keepalive: bool
    log_msg: str


snapshot_scenarios = [
    SnapshotScenario(
        id="basic",
        append_flags=[],
        check_yaml=False,
        expected_output="Snapshot complete",
        expected_in_file=None,
        expected_not_in_file=None,
        keepalive=False,
        log_msg="Basic snapshot",
    ),
    SnapshotScenario(
        id="active_env",
        append_flags=[],
        check_yaml=True,
        expected_output="Creating snapshot of active environment",
        expected_in_file=["--module file-access-control", "--module test"],
        expected_not_in_file=None,
        keepalive=True,
        log_msg="Snapshot of active environment",
    ),
    SnapshotScenario(
        id="cluster_resources",
        append_flags=[],
        check_yaml=False,
        expected_output="Snapshotting root resources only",
        expected_in_file=None,
        expected_not_in_file=None,
        keepalive=False,
        log_msg="Snapshot of cluster resources only",
    ),
    SnapshotScenario(
        id="specified_modules",
        append_flags=["--module", "test"],
        check_yaml=True,
        expected_output="Creating snapshot of specified modules",
        expected_in_file=None,
        expected_not_in_file=None,
        keepalive=False,
        log_msg="Snapshot of specified modules",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg,provision_clusters",
    [
        (sc, getattr(sc, "log_msg", ""), {"keepalive": getattr(sc, "keepalive", False)})
        for sc in snapshot_scenarios
    ],
    ids=utils.get_scenario_ids(snapshot_scenarios),
    indirect=["log_msg", "provision_clusters"],
)
@pytest.mark.usefixtures("provision_clusters")
def test_snapshot_scenarios(scenario: SnapshotScenario) -> None:
    """Run each SnapshotScenario."""
    if not scenario.append_flags:
        append_flags = CMD_SNAPSHOT_TEST["append"]
    else:
        append_flags = list(CMD_SNAPSHOT_TEST["append"] + scenario.append_flags)

    cmd_args = copy.deepcopy(CMD_SNAPSHOT)
    cmd_args["append"] = append_flags
    result = executor.exec(executor.build_cmd(**cmd_args))
    if scenario.check_yaml:
        utils.assert_is_file(snapshot_test_yaml_file(SNAPSHOT_NAME))
    utils.assert_exit_code(result)
    if scenario.expected_output:
        utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_in_file:
        if isinstance(scenario.expected_in_file, list):
            for item in scenario.expected_in_file:
                utils.assert_in_file(item, path=snapshot_provision_file(SNAPSHOT_NAME))
        else:
            utils.assert_in_file(
                scenario.expected_in_file,
                path=snapshot_provision_file(SNAPSHOT_NAME),
            )
    if scenario.expected_not_in_file:
        if isinstance(scenario.expected_not_in_file, list):
            for item in scenario.expected_not_in_file:
                utils.assert_not_in_file(item, path=snapshot_config_file(SNAPSHOT_NAME))
        else:
            utils.assert_not_in_file(
                scenario.expected_not_in_file,
                path=snapshot_config_file(SNAPSHOT_NAME),
            )
    if os.path.isfile(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg")):
        utils.assert_is_file(snapshot_config_file(SNAPSHOT_NAME))
    provision_file = snapshot_provision_file(SNAPSHOT_NAME)
    utils.assert_is_file(provision_file)
    utils.assert_is_file(os.path.join(SNAPSHOT_DIR, f"{SNAPSHOT_NAME}.tar.gz"))
    utils.assert_in_file("minitrino -v --env LIB_PATH=", path=provision_file)


SNAPSHOT_INVALID_NAME_MSG = "Testing invalid snapshot name: ##.my-test?"


@pytest.mark.parametrize("log_msg", [SNAPSHOT_INVALID_NAME_MSG], indirect=True)
def test_invalid_name() -> None:
    """Test invalid snapshot name."""
    cmd_args = CMD_SNAPSHOT.copy()
    cmd_args["append"] = ["--name", "##.my-test?"]
    result = executor.exec(executor.build_cmd(**cmd_args))
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output("Illegal character", result=result)


TEST_DIRECTORY_MSG = "Testing snapshot to user-specified directory: /tmp/"


@pytest.mark.parametrize("log_msg", [TEST_DIRECTORY_MSG], indirect=True)
def test_directory() -> None:
    """
    Test that the snapshot file can be saved in a user-specified
    directory.
    """
    cmd_args = copy.deepcopy(CMD_SNAPSHOT_TEST)
    cmd_args["append"].extend(["--directory", "/tmp/"])
    result = executor.exec(executor.build_cmd(**cmd_args), "y\n")
    run_assertions(
        result, check_path=os.path.join(os.sep, "tmp"), check_default_paths=False
    )
    os.remove(os.path.join(os.sep, "tmp", "test.tar.gz"))
    shutil.rmtree(os.path.join(os.sep, "tmp", SNAPSHOT_NAME), ignore_errors=True)


TEST_DIRECTORY_INVALID_MSG = "Testing snapshot to invalid directory: /foo/"


@pytest.mark.parametrize("log_msg", [TEST_DIRECTORY_INVALID_MSG], indirect=True)
def test_directory_invalid() -> None:
    """
    Test that the snapshot file cannot be saved in an invalid directory.
    """
    cmd = append_snapshot_test_cmd(["--directory", "/foo/"])
    result = executor.exec(cmd, "y\n")
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(
        "Cannot save snapshot in nonexistent directory:", result=result
    )


SNAPSHOT_PROVISION_FILE_MSG = "Testing snapshot provision file execution"


@pytest.mark.parametrize("log_msg", [SNAPSHOT_PROVISION_FILE_MSG], indirect=True)
def test_provision_file() -> None:
    """Test snapshot `provision-snapshot.sh` execution."""
    provision = executor.build_cmd(base="provision", append=["--module", "test"])
    executor.exec(provision)
    cmd_args = copy.deepcopy(CMD_SNAPSHOT_TEST)
    cmd_args["append"].extend(["--module", "test"])
    executor.exec(executor.build_cmd(**cmd_args), "y\n")
    executor.exec(executor.build_cmd(base="down", append=["--sig-kill"]))
    provision_file = snapshot_provision_file()
    output = common.execute_cmd(f"bash {provision_file}")
    utils.assert_exit_code(output)
    utils.assert_in_output("Environment provisioning complete", result=output)


SNAPSHOT_FORCE_MSG = "Testing --force option for snapshot command"


@pytest.mark.parametrize("log_msg", [SNAPSHOT_FORCE_MSG], indirect=True)
def test_force() -> None:
    """Verify overwrite of existing snapshot."""
    cmd_args = copy.deepcopy(CMD_SNAPSHOT_TEST)
    cmd_args["append"].extend(["--module", "test"])
    executor.exec(executor.build_cmd(**cmd_args))
    result = executor.exec(append_snapshot_test_cmd(["--force"]))
    run_assertions(result, check_yaml=False)
    utils.assert_in_output("Overwriting...", result=result)


TEST_NO_SCRUB_MSG = "Testing --no-scrub option for snapshot command"


@pytest.mark.parametrize("log_msg", [TEST_NO_SCRUB_MSG], indirect=True)
@pytest.mark.usefixtures("cleanup_config")
def test_no_scrub() -> None:
    """
    Verify that the user config file is retained in full when scrubbing
    is disabled.
    """
    result = executor.exec(append_snapshot_test_cmd(["--no-scrub"]), "y\n")
    run_assertions(result, check_yaml=False)
    utils.assert_not_in_file(SCRUBBED, path=snapshot_config_file())


TEST_SCRUB_MSG = "Testing scrubbing enabled for snapshot command"


@pytest.mark.usefixtures("cleanup_config")
@pytest.mark.parametrize("log_msg", [TEST_SCRUB_MSG], indirect=True)
def test_scrub() -> None:
    """Verify that sensitive data in user config file is scrubbed."""
    cmd_args = copy.deepcopy(CMD_SNAPSHOT_TEST)
    cmd_args["append"].extend(["--module", "test"])
    result = executor.exec(executor.build_cmd(**cmd_args))
    run_assertions(result, check_yaml=False)
    utils.assert_in_file(SCRUBBED, path=snapshot_config_file())


def append_snapshot_test_cmd(append_flags: list[str] = []) -> list[str]:
    """Build the snapshot command with the given append flags."""
    cmd_args = copy.deepcopy(CMD_SNAPSHOT_TEST)
    cmd_args["append"].extend(append_flags)
    return executor.build_cmd(**cmd_args)


def snapshot_test_yaml_file(snapshot_name: str = "test") -> str:
    """Return the path to the test snapshot yaml file."""
    return os.path.join(
        MINITRINO_USER_SNAPSHOTS_DIR,
        snapshot_name,
        "lib",
        "modules",
        "catalog",
        "test",
        "test.yaml",
    )


def snapshot_config_file(snapshot_name: str = "test") -> str:
    """Return the path to the test snapshot config file."""
    return os.path.join(MINITRINO_USER_SNAPSHOTS_DIR, snapshot_name, "minitrino.cfg")


def snapshot_provision_file(snapshot_name: str = "test") -> str:
    """Return the path to the test snapshot provision file."""
    return os.path.join(
        MINITRINO_USER_SNAPSHOTS_DIR, snapshot_name, "provision-snapshot.sh"
    )


def run_assertions(
    result: common.CommandResult | Result,
    snapshot_name: str = "test",
    check_path: str = SNAPSHOT_DIR,
    check_default_paths: bool = True,
    check_yaml: bool = True,
) -> None:
    """Run standard assertions for the snapshot command."""
    utils.assert_exit_code(result)
    utils.assert_in_output("Snapshot complete", result=result)
    utils.assert_is_file(os.path.join(check_path, f"{snapshot_name}.tar.gz"))
    if check_default_paths:
        if check_yaml:
            utils.assert_is_file(snapshot_test_yaml_file(snapshot_name))
        provision_file = snapshot_provision_file(snapshot_name)
        utils.assert_is_file(provision_file)
        utils.assert_in_file("minitrino -v --env LIB_PATH=", path=provision_file)
        if os.path.isfile(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg")):
            utils.assert_is_file(snapshot_config_file(snapshot_name))
