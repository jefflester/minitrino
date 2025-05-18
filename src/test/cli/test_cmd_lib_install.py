import os

from logging import Logger
from dataclasses import dataclass
from typing import Optional, Any
from pytest.mark import parametrize, usefixtures

from test.cli import utils
from test.common import MINITRINO_USER_DIR

CMD_INSTALL = {"base": "lib-install", "append": ["--version", "0.0.0"]}


@dataclass
class LibInstallScenario:
    """
    Library install scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    cmd : dict[str, Any]
        Command line arguments to pass to the lib-install command.
    input_val : Optional[str]
        Input value to pass to the lib-install command.
    expected_exit_code : int
        Expected exit code of the lib-install command.
    expected_output : Optional[str]
        Expected string to be in the output of the lib-install command.
    log_msg : str
        Log message to display before running the test.
    """

    id: str
    cmd: dict[str, Any]
    input_val: Optional[str]
    expected_exit_code: int
    expected_output: Optional[str]
    log_msg: str


lib_install_scenarios = [
    LibInstallScenario(
        id="install",
        cmd=CMD_INSTALL,
        input_val=None,
        expected_exit_code=0,
        expected_output=None,
        log_msg="Install library (normal)",
    ),
    LibInstallScenario(
        id="install_overwrite",
        cmd=CMD_INSTALL,
        input_val="y\n",
        expected_exit_code=0,
        expected_output="Removing existing library directory",
        log_msg="Install library with overwrite",
    ),
    LibInstallScenario(
        id="invalid_version",
        cmd={"base": "lib-install", "append": ["--version", "foo"]},
        input_val=None,
        expected_exit_code=1,
        expected_output=None,
        log_msg="Install library with invalid version",
    ),
]


@parametrize(
    "scenario", lib_install_scenarios, ids=utils.get_scenario_ids(lib_install_scenarios)
)
@usefixtures("log_test")
def test_lib_install_scenarios(
    scenario: LibInstallScenario,
    logger: Logger,
) -> None:
    """Run each LibInstallScenario."""
    cli_cmd = utils.build_cmd(**scenario.cmd)
    result = utils.cli_cmd(cli_cmd, logger, scenario.input_val)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_is_dir(os.path.join(MINITRINO_USER_DIR, "lib"))
    if scenario.expected_output:
        utils.assert_in_output(scenario.expected_output, result=result)
