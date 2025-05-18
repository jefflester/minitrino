import os
import shutil

from logging import Logger
from dataclasses import dataclass
from typing import Callable, Optional
from pytest.mark import parametrize, usefixtures

from test import common
from test.cli import utils
from test.common import (
    SNAPSHOT_DIR,
    MINITRINO_USER_SNAPSHOTS_DIR,
    MINITRINO_USER_DIR,
)

CMD_SNAPSHOT = {"base": "snapshot"}
CMD_SNAPSHOT_TEST = {"base": "snapshot", "append": ["--name", "test"]}
CMD_PROVISION = ["-v", "provision", "--module", "test"]
CMD_DOWN = ["-v", "down", "--sig-kill"]


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


def snapshot_parametrize_args():
    return [
        pytest.param(
            scenario,
            "my-test_123",
            f"Testing snapshot scenario: {getattr(scenario, 'snapshot_name', 'unknown')}",
            id=scenario.snapshot_name if hasattr(scenario, "snapshot_name") else str(i),
        )
        for i, scenario in enumerate(snapshot_scenarios)
    ]


def run_assertions(
    result: any,
    check_yaml: bool = True,
    snapshot_name: str = "test",
    check_path: str = SNAPSHOT_DIR,
    logger: Logger = Logger,
) -> None:
    """Run standard assertions for the snapshot command."""
    logger.info(f"Running snapshot assertions for: {snapshot_name}")
    if check_yaml:
        logger.debug(
            f"Checking YAML file for snapshot: {snapshot_test_yaml_file(snapshot_name)}"
        )
        utils.assert_is_file(snapshot_test_yaml_file(snapshot_name))
    utils.assert_exit_code(result)
    utils.assert_in_output("Snapshot complete", result=result)
    if os.path.isfile(os.path.join(MINITRINO_USER_DIR, "minitrino.cfg")):
        logger.debug(
            f"Checking config file for snapshot: {snapshot_config_file(snapshot_name)}"
        )
        utils.assert_is_file(snapshot_config_file(snapshot_name))
    provision_file = snapshot_provision_file(snapshot_name)
    utils.assert_is_file(provision_file)
    utils.assert_is_file(os.path.join(check_path, f"{snapshot_name}.tar.gz"))
    utils.assert_in_file("minitrino -v --env LIB_PATH=", provision_file)
    logger.info(f"Snapshot assertions passed for: {snapshot_name}")


@dataclass
class SnapshotScenario:
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


snapshot_scenarios = [
    SnapshotScenario(
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
    ),
    SnapshotScenario(
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
    ),
    SnapshotScenario(
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
    ),
    SnapshotScenario(
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
    ),
]


@parametrize(
    "scenario,cleanup_snapshot,log_msg",
    snapshot_parametrize_args(),
    indirect=["cleanup_snapshot", "log_msg"],
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_snapshot_scenarios(
    scenario: SnapshotScenario,
    logger: Logger,
) -> None:
    """
    Run each SnapshotScenario.

    Parameters
    ----------
    scenario : SnapshotScenario
        The scenario to run.
    logger : Logger
        Logger to use for logging.
    """
    if scenario.setup:
        logger.info("Running scenario setup function.")
        scenario.setup()
    cmd = utils.build_cmd(scenario.cmd, append=scenario.append_flags)
    result = utils.cli_cmd(cmd, logger, scenario.input_val)
    if scenario.check_yaml:
        logger.debug(
            f"Checking YAML file for snapshot: {snapshot_test_yaml_file(scenario.snapshot_name)}"
        )
        utils.assert_is_file(snapshot_test_yaml_file(scenario.snapshot_name))
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    if scenario.expected_output:
        logger.debug(f"Checking expected output: {scenario.expected_output}")
        utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_in_file:
        logger.debug(f"Checking expected content in file: {scenario.expected_in_file}")
        if isinstance(scenario.expected_in_file, list):
            for item in scenario.expected_in_file:
                utils.assert_in_file(
                    item, snapshot_provision_file(scenario.snapshot_name)
                )
        else:
            utils.assert_in_file(
                scenario.expected_in_file,
                snapshot_provision_file(scenario.snapshot_name),
            )
    if scenario.expected_not_in_file:
        logger.debug(f"Checking content NOT in file: {scenario.expected_not_in_file}")
        if isinstance(scenario.expected_not_in_file, list):
            for item in scenario.expected_not_in_file:
                utils.assert_not_in_file(
                    item, snapshot_config_file(scenario.snapshot_name)
                )
        else:
            utils.assert_not_in_file(
                scenario.expected_not_in_file,
                snapshot_config_file(scenario.snapshot_name),
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
    utils.assert_in_file("minitrino -v --env LIB_PATH=", provision_file)


@parametrize(
    "cleanup_snapshot,log_msg",
    [
        pytest.param(
            **{
                "cleanup_snapshot": "my-test_123",
                "log_msg": "Testing snapshot with valid name",
            },
            id="valid_name",
        ),
    ],
    indirect=["cleanup_snapshot", "log_msg"],
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_valid_name(logger: Logger):
    """Test valid snapshot name."""
    cmd = utils.build_cmd(
        **CMD_SNAPSHOT, append=["--name", "my-test_123", "--module", "test"]
    )
    result = utils.cli_cmd(cmd, logger, "y\n")
    run_assertions(result, snapshot_name="my-test_123", logger=logger)
    utils.assert_in_output("Creating snapshot of specified modules", result=result)


@parametrize(
    "log_msg",
    [pytest.param("Testing invalid snapshot name: ##.my-test?", id="invalid_name")],
    indirect=True,
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_invalid_name(logger: Logger) -> None:
    """
    Test invalid snapshot name.

    Parameters
    ----------
    logger : Logger
        Logger to use for logging.
    """
    cmd = utils.build_cmd(
        **CMD_SNAPSHOT, append=["--name", "##.my-test?", "--module", "test"]
    )
    result = utils.cli_cmd(cmd, logger, "y\n")
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(
        "Illegal character found in provided filename", result=result
    )


@parametrize(
    "log_msg",
    [
        pytest.param(
            "Testing snapshot to user-specified directory: /tmp/",
            id="specific_directory",
        )
    ],
    indirect=True,
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_specific_directory(logger: Logger) -> None:
    """
    Test that the snapshot file can be saved in a user-specified directory.

    Parameters
    ----------
    logger : Logger
        Logger to use for logging.
    """
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST, append=["--directory", "/tmp/"])
    result = utils.cli_cmd(cmd, logger, "y\n")
    run_assertions(result, True, check_path=os.path.join(os.sep, "tmp"), logger=logger)
    utils.assert_in_output("Creating snapshot of specified modules", result=result)
    os.remove(os.path.join(os.sep, "tmp", "test.tar.gz"))


@parametrize(
    "log_msg",
    [
        pytest.param(
            "Testing snapshot to invalid directory: /tmppp/",
            id="specific_directory_invalid",
        )
    ],
    indirect=True,
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_specific_directory_invalid(logger: Logger) -> None:
    """
    Test that the snapshot file cannot be saved in an invalid directory.

    Parameters
    ----------
    logger : Logger
        Logger to use for logging.
    """
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST, append=["--directory", "/tmppp/"])
    result = utils.cli_cmd(cmd, logger, "y\n")
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(
        "Cannot save snapshot in nonexistent directory:", result=result
    )


@parametrize(
    "log_msg",
    [pytest.param("Testing snapshot provision file execution", id="provision_file")],
    indirect=True,
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_provision_file(logger: Logger) -> None:
    """
    Test snapshot `provision-snapshot.sh` execution.

    Parameters
    ----------
    logger : Logger
        Logger to use for logging.
    """
    utils.cli_cmd(CMD_PROVISION, logger)
    utils.cli_cmd(CMD_SNAPSHOT_TEST, logger, "y\n")
    utils.cli_cmd(CMD_DOWN, logger)
    provision_file = snapshot_provision_file()
    logger.debug(f"Executing provision file: {provision_file}")
    output = common.execute_cmd(["sh", provision_file])
    utils.assert_exit_code(output)
    utils.assert_in_output("Environment provisioning complete", result=output)


@parametrize(
    "log_msg",
    [pytest.param("Testing --force option for snapshot command", id="force")],
    indirect=True,
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_force(logger: Logger) -> None:
    """
    Verify overwrite of existing snapshot.

    Parameters
    ----------
    logger : Logger
        Logger to use for logging.
    """
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST, append=["--force"])
    result = utils.cli_cmd(cmd, logger, "y\n")
    run_assertions(result, logger=logger)
    utils.assert_in_output("Creating snapshot of specified modules", result=result)


@parametrize(
    "log_msg",
    [pytest.param("Testing --no-scrub option for snapshot command", id="no_scrub")],
    indirect=True,
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_no_scrub(logger: Logger) -> None:
    """
    Verify that the user config file is retained in full when scrubbing is disabled.

    Parameters
    ----------
    logger : Logger
        Logger to use for logging.
    """
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST, append=["--no-scrub"])
    result = utils.cli_cmd(cmd, logger, "y\n")
    run_assertions(result, logger=logger)
    utils.assert_not_in_file("*" * 20, snapshot_config_file())


@parametrize(
    "log_msg",
    [pytest.param("Testing scrubbing enabled for snapshot command", id="scrub")],
    indirect=True,
)
@usefixtures("log_test", "down", "cleanup_snapshot")
def test_scrub(logger: Logger) -> None:
    """
    Verify that sensitive data in user config file is scrubbed.

    Parameters
    ----------
    logger : Logger
        Logger to use for logging.
    """
    cmd = utils.build_cmd(**CMD_SNAPSHOT_TEST)
    result = utils.cli_cmd(cmd, logger, "y\n")
    run_assertions(result, logger=logger)
    utils.assert_in_file("*" * 20, snapshot_config_file())
