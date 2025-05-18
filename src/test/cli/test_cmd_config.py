import os
import shutil

from logging import Logger
from dataclasses import dataclass
from typing import Callable, Optional
from pytest.mark import parametrize, usefixtures

from test.cli import utils
from test.common import MINITRINO_USER_DIR, CONFIG_FILE

CMD = {"base": "config", "prepend": ["-v", "-e", "TEXT_EDITOR=cat"]}


@dataclass
class ConfigScenario:
    """
    Config file scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    setup : Optional[Callable]
        Setup function to run before the test.
    cmd_args : list[str]
        Command line arguments to pass to the config command.
    input_val : Optional[str]
        Input value to pass to the config command.
    expected_exit_code : int
        Expected exit code of the config command.
    expected_dir : bool
        Whether the config directory is expected to exist.
    expected_file : bool
        Whether the config file is expected to exist.
    expected_in_output : Optional[str]
        Expected string to be in the output of the config command.
    expected_not_in_file : Optional[str]
        Expected string to NOT be in the config file.
    log_msg : str
        Log message to display before running the test.
    """

    id: str
    setup: Optional[Callable]
    cmd_args: list[str]
    input_val: Optional[str]
    expected_exit_code: int
    expected_dir: bool
    expected_file: bool
    expected_in_output: Optional[str]
    expected_not_in_file: Optional[str]
    log_msg: str


config_scenarios = [
    ConfigScenario(
        id="no_directory",
        setup=lambda: shutil.rmtree(MINITRINO_USER_DIR, ignore_errors=True),
        cmd_args=[],
        input_val=None,
        expected_exit_code=0,
        expected_dir=True,
        expected_file=True,
        expected_in_output=None,
        expected_not_in_file=None,
        log_msg="Testing config: creates directory and config file when missing",
    ),
    ConfigScenario(
        id="no_config_file",
        setup=lambda: os.path.isfile(CONFIG_FILE) and os.remove(CONFIG_FILE),
        cmd_args=[],
        input_val=None,
        expected_exit_code=0,
        expected_dir=False,
        expected_file=True,
        expected_in_output=None,
        expected_not_in_file=None,
        log_msg="Testing config: creates config file when only config is missing",
    ),
    ConfigScenario(
        id="reset_invalid",
        setup=lambda: utils.write_file(CONFIG_FILE, "hello world"),
        cmd_args=["--reset"],
        input_val="y\n",
        expected_exit_code=0,
        expected_dir=False,
        expected_file=True,
        expected_in_output=None,
        expected_not_in_file="hello world",
        log_msg="Testing config: resets invalid config file",
    ),
    ConfigScenario(
        id="edit_invalid",
        setup=lambda: utils.write_file(CONFIG_FILE, "hello world"),
        cmd_args=[],
        input_val=None,
        expected_exit_code=0,
        expected_dir=False,
        expected_file=False,
        expected_in_output="Failed to parse config file",
        expected_not_in_file=None,
        log_msg="Testing config: fails with invalid config file",
    ),
]


@parametrize(
    "scenario",
    config_scenarios,
    ids=utils.get_scenario_ids(config_scenarios),
)
@usefixtures("log_test", "cleanup_config")
def test_config_scenarios(
    scenario: ConfigScenario,
    logger: Logger,
) -> None:
    """Run each ConfigScenario."""
    if scenario.setup:
        logger.debug("Running setup function for scenario.")
        scenario.setup()
    cmd = utils.build_cmd(**CMD, append=scenario.cmd_args)
    result = utils.cli_cmd(cmd, logger, scenario.input_val)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    if scenario.expected_dir:
        utils.assert_is_dir(MINITRINO_USER_DIR)
    if scenario.expected_file:
        utils.assert_is_file(CONFIG_FILE)
    if scenario.expected_in_output:
        utils.assert_in_output(scenario.expected_in_output, result=result)
    if scenario.expected_not_in_file:
        utils.assert_not_in_file(scenario.expected_not_in_file, CONFIG_FILE)


@usefixtures("log_test", "cleanup_config")
@parametrize("log_msg", ["Testing edit valid config"], indirect=True)
def test_edit_valid_config(logger: Logger) -> None:
    """Verify the user can edit an existing configuration file."""
    result = utils.cli_cmd(utils.build_cmd(**CMD), logger)
    utils.assert_exit_code(result)
