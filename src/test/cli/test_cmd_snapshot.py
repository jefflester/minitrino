import os
import shutil
from dataclasses import dataclass
from typing import Callable, Optional

import pytest

from test import common
from test.cli import utils
from test.cli.utils import logger
from test.common import (
    MINITRINO_USER_DIR,
    MINITRINO_USER_SNAPSHOTS_DIR,
    SNAPSHOT_DIR,
)

CMD_SNAPSHOT = {"base": "snapshot"}
CMD_SNAPSHOT_TEST = {"base": "snapshot", "append": ["--name", "test"]}
CMD_PROVISION = ["-v", "provision", "--module", "test"]
CMD_DOWN = ["-v", "down", "--sig-kill"]


@dataclass
class SnapshotScenario:
    """
    Snapshot scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    setup : Optional[Callable]
        Setup function to run before the test.
    cmd : str
        Command to run.
    append_flags : list[str]
        Flags to append to the command.
    input_val : Optional[str]
        Input value for the command.
    check_yaml : bool
        Whether to check the YAML file.
    snapshot_name : str
        Name of the snapshot.
    check_path : str
        Path to check.
    expected_exit_code : int
        Expected exit code.
    expected_output : Optional[str]
        Expected output.
    expected_in_file : Optional[str | list[str]]
        Expected content in file.
    expected_not_in_file : Optional[str | list[str]]
        Expected content NOT in file.
    log_msg : str
        Log message.
    """

    id: str
    setup: Optional[Callable]
    cmd: str
    append_flags: list[str]
    input_val: Optional[str]
    check_yaml: bool
    snapshot_name: str
    check_path: str
    expected_exit_code: int
    expected_output: Optional[str]
    expected_in_file: Optional[str | list[str]]
    expected_not_in_file: Optional[str | list[str]]
    log_msg: str


snapshot_scenarios = [
    SnapshotScenario(
        id="basic",
        setup=lambda: shutil.rmtree(MINITRINO_USER_SNAPSHOTS_DIR),
        cmd=CMD_SNAPSHOT,
        append_flags=["--name", "test", "--module", "test"],
        input_val="y\n",
        check_yaml=True,
        snapshot_name="test",
        check_path=SNAPSHOT_DIR,
        expected_exit_code=0,
        expected_output="Snapshot complete",
        expected_in_file=None,
        expected_not_in_file=None,
        log_msg="Basic snapshot scenario",
    ),
    SnapshotScenario(
        id="active_env",
        setup=None,
        cmd=CMD_SNAPSHOT,
        append_flags=["--name", "test"],
        input_val="y\n",
        check_yaml=False,
        snapshot_name="test",
        check_path=SNAPSHOT_DIR,
        expected_exit_code=0,
        expected_output="Creating snapshot of active environment",
        expected_in_file=["--module file-access-control", "--module test"],
        expected_not_in_file=None,
        log_msg="Snapshot of active environment",
    ),
    SnapshotScenario(
        id="cluster_resources",
        setup=None,
        cmd=CMD_SNAPSHOT,
        append_flags=["--name", "test"],
        input_val="y\n",
        check_yaml=False,
        snapshot_name="test",
        check_path=SNAPSHOT_DIR,
        expected_exit_code=0,
        expected_output="Creating snapshot of cluster resources only",
        expected_in_file=None,
        expected_not_in_file=None,
        log_msg="Snapshot of cluster resources only",
    ),
    SnapshotScenario(
        id="specified_modules",
        setup=None,
        cmd=CMD_SNAPSHOT,
        append_flags=["--name", "test", "--module", "test"],
        input_val="y\n",
        check_yaml=True,
        snapshot_name="test",
        check_path=SNAPSHOT_DIR,
        expected_exit_code=0,
        expected_output="Creating snapshot of specified modules",
        expected_in_file=None,
        expected_not_in_file=None,
        log_msg="Snapshot of specified modules",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(snapshot_scenarios),
    ids=utils.get_scenario_ids(snapshot_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
def test_snapshot_scenarios(scenario: SnapshotScenario) -> None:
    """Run each SnapshotScenario."""
    if scenario.setup:
        logger.debug("Running scenario setup function.")
        scenario.setup()
    cmd = utils.build_cmd(scenario.cmd, append=scenario.append_flags)
    result = utils.cli_cmd(cmd, scenario.input_val)
    if scenario.check_yaml:
        logger.debug(
            f"Checking YAML file for snapshot: {snapshot_test_yaml_file(scenario.snapshot_name)}",
        )
        utils.assert_is_file(snapshot_test_yaml_file(scenario.snapshot_name))
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    if scenario.expected_output:
        logger.debug(f"Checking expected output: {scenario.expected_output}")
        utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_in_file:
        logger.debug(
            f"Checking expected content in file: {scenario.expected_in_file}", "debug"
        )
        if isinstance(scenario.expected_in_file, list):
            for item in scenario.expected_in_file:
                utils.assert_in_file(
                    item, path=snapshot_provision_file(scenario.snapshot_name)
                )
        else:
            utils.assert_in_file(
                scenario.expected_in_file,
                path=snapshot_provision_file(scenario.snapshot_name),
            )
    if scenario.expected_not_in_file:
        logger.debug(f"Checking content NOT in file: {scenario.expected_not_in_file}")
        if isinstance(scenario.expected_not_in_file, list):
            for item in scenario.expected_not_in_file:
                utils.assert_not_in_file(
                    item, path=snapshot_config_file(scenario.snapshot_name)
                )
        else:
            utils.assert_not_in_file(
                scenario.expected_not_in_file,
                path=snapshot_config_file(scenario.snapshot_name),
            )
    if os.path.isfile(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg")):
        logger.debug(
            f"Checking config file for snapshot: {snapshot_config_file(scenario.snapshot_name)}"
        )
        utils.assert_is_file(snapshot_config_file(scenario.snapshot_name))
    provision_file = snapshot_provision_file(scenario.snapshot_name)
    utils.assert_is_file(provision_file)
    utils.assert_is_file(
        os.path.join(scenario.check_path, f"{scenario.snapshot_name}.tar.gz")
    )
    utils.assert_in_file("minitrino -v --env LIB_PATH=", path=provision_file)


@pytest.mark.parametrize(
    ("log_msg", "cleanup_snapshot"),
    [("Testing snapshot with valid name", "my-test_123")],
    indirect=True,
)
@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
def test_valid_name():
    """Test valid snapshot name."""
    cmd = utils.build_cmd(
        **CMD_SNAPSHOT, append=["--name", "my-test_123", "--module", "test"]
    )
    result = utils.cli_cmd(cmd, "y\n")
    run_assertions(result, snapshot_name="my-test_123")
    utils.assert_in_output("Creating snapshot of specified modules", result=result)


SNAPSHOT_INVALID_NAME_MSG = "Testing invalid snapshot name: ##.my-test?"


@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
@pytest.mark.parametrize("log_msg", [SNAPSHOT_INVALID_NAME_MSG], indirect=True)
def test_invalid_name() -> None:
    """Test invalid snapshot name."""
    cmd = utils.build_cmd(
        **CMD_SNAPSHOT, append=["--name", "##.my-test?", "--module", "test"]
    )
    result = utils.cli_cmd(cmd, "y\n")
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(
        "Illegal character found in provided filename", result=result
    )


TEST_SPECIFIC_DIR_MSG = "Testing snapshot to user-specified directory: /tmp/"


@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
@pytest.mark.parametrize("log_msg", [TEST_SPECIFIC_DIR_MSG], indirect=True)
def test_specific_directory() -> None:
    """
    Test that the snapshot file can be saved in a user-specified
    directory.
    """
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST, append=["--directory", "/tmp/"])
    result = utils.cli_cmd(cmd, "y\n")
    run_assertions(result, True, check_path=os.path.join(os.sep, "tmp"))
    utils.assert_in_output("Creating snapshot of specified modules", result=result)
    os.remove(os.path.join(os.sep, "tmp", "test.tar.gz"))


TEST_SPECIFIC_DIR_INVALID_MSG = "Testing snapshot to invalid directory: /tmppp/"


@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
@pytest.mark.parametrize("log_msg", [TEST_SPECIFIC_DIR_INVALID_MSG], indirect=True)
def test_specific_directory_invalid() -> None:
    """
    Test that the snapshot file cannot be saved in an invalid directory.
    """
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST, append=["--directory", "/tmppp/"])
    result = utils.cli_cmd(cmd, "y\n")
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(
        "Cannot save snapshot in nonexistent directory:", result=result
    )


SNAPSHOT_PROVISION_FILE_MSG = "Testing snapshot provision file execution"


@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
@pytest.mark.parametrize("log_msg", [SNAPSHOT_PROVISION_FILE_MSG], indirect=True)
def test_provision_file() -> None:
    """Test snapshot `provision-snapshot.sh` execution."""
    utils.cli_cmd(CMD_PROVISION)
    utils.cli_cmd(CMD_SNAPSHOT_TEST, "y\n")
    utils.cli_cmd(CMD_DOWN)
    provision_file = snapshot_provision_file()
    logger.debug(f"Executing provision file: {provision_file}")
    output = common.execute_cmd(["sh", provision_file])
    utils.assert_exit_code(output)
    utils.assert_in_output("Environment provisioning complete", result=output)


SNAPSHOT_FORCE_MSG = "Testing --force option for snapshot command"


@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
@pytest.mark.parametrize("log_msg", [SNAPSHOT_FORCE_MSG], indirect=True)
def test_force() -> None:
    """Verify overwrite of existing snapshot."""
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST, append=["--force"])
    result = utils.cli_cmd(cmd, "y\n")
    run_assertions(result)
    utils.assert_in_output("Creating snapshot of specified modules", result=result)


TEST_NO_SCRUB_MSG = "Testing --no-scrub option for snapshot command"


@pytest.mark.parametrize("log_msg", [TEST_NO_SCRUB_MSG], indirect=True)
@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
def test_no_scrub() -> None:
    """
    Verify that the user config file is retained in full when scrubbing
    is disabled.
    """
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST, append=["--no-scrub"])
    result = utils.cli_cmd(cmd, "y\n")
    run_assertions(result)
    utils.assert_not_in_file("*" * 20, path=snapshot_config_file())


TEST_SCRUB_MSG = "Testing scrubbing enabled for snapshot command"


@pytest.mark.usefixtures("log_test", "down", "cleanup_snapshot")
@pytest.mark.parametrize("log_msg", [TEST_SCRUB_MSG], indirect=True)
def test_scrub() -> None:
    """Verify that sensitive data in user config file is scrubbed."""
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST)
    result = utils.cli_cmd(cmd, "y\n")
    run_assertions(result)
    utils.assert_in_file("*" * 20, path=snapshot_config_file())


def snapshot_test_yaml_file(snapshot_name: str = "test") -> str:
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
    return os.path.join(MINITRINO_USER_SNAPSHOTS_DIR, snapshot_name, "minitrino.cfg")


def snapshot_provision_file(snapshot_name: str = "test") -> str:
    return os.path.join(
        MINITRINO_USER_SNAPSHOTS_DIR, snapshot_name, "provision-snapshot.sh"
    )


def run_assertions(
    result: any,
    check_yaml: bool = True,
    snapshot_name: str = "test",
    check_path: str = SNAPSHOT_DIR,
) -> None:
    """Run standard assertions for the snapshot command."""
    utils.debug(f"Running snapshot assertions for: {snapshot_name}")
    if check_yaml:
        utils.debug(
            f"Checking YAML file for snapshot: {snapshot_test_yaml_file(snapshot_name)}",
        )
        utils.assert_is_file(snapshot_test_yaml_file(snapshot_name))
    utils.assert_exit_code(result)
    utils.assert_in_output("Snapshot complete", result=result)
    if os.path.isfile(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg")):
        logger.debug(
            f"Checking config file for snapshot: {snapshot_config_file(snapshot_name)}",
        )
        utils.assert_is_file(snapshot_config_file(snapshot_name))
    provision_file = snapshot_provision_file(snapshot_name)
    utils.assert_is_file(provision_file)
    utils.assert_is_file(os.path.join(check_path, f"{snapshot_name}.tar.gz"))
    utils.assert_in_file("minitrino -v --env LIB_PATH=", path=provision_file)
    logger.debug(f"Snapshot assertions passed for: {snapshot_name}")
