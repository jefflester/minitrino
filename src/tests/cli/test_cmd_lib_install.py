import os
import shutil
from dataclasses import dataclass
from typing import Any, Optional

import pytest

from tests.cli import utils
from tests.common import MINITRINO_USER_DIR

CMD_INSTALL = {"base": "lib-install", "append": ["--version", "0.0.0"]}
LIB_DIR = os.path.join(MINITRINO_USER_DIR, "lib")


@pytest.fixture(autouse=True, scope="module")
def clean_before_test():
    """Clean up the lib directory before and after tests."""

    def _uninstall():
        if os.path.isdir(LIB_DIR):
            utils.logger.debug(f"Removing existing library directory: {LIB_DIR}")
            shutil.rmtree(LIB_DIR)

    _uninstall()
    yield
    _uninstall()


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
        log_msg="Overwrite existing library",
    ),
    LibInstallScenario(
        id="invalid_version",
        cmd={"base": "lib-install", "append": ["--version", "foo"]},
        input_val=None,
        expected_exit_code=2,
        expected_output="X.Y.Z format",
        log_msg="Install library with invalid version",
    ),
    LibInstallScenario(
        id="invalid_version",
        cmd={"base": "lib-install", "append": ["--version", "9.9.9"]},
        input_val=None,
        expected_exit_code=1,
        expected_output="not found",
        log_msg="Install library with valid but non-existent version",
    ),
    LibInstallScenario(
        id="list_releases",
        cmd={"base": "lib-install", "append": ["--list-releases"]},
        input_val=None,
        expected_exit_code=0,
        expected_output="Available Minitrino releases:",
        log_msg="List library releases",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(lib_install_scenarios),
    ids=utils.get_scenario_ids(lib_install_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("log_test")
def test_lib_install_scenarios(
    scenario: LibInstallScenario,
) -> None:
    """Run each LibInstallScenario."""
    cli_cmd = utils.build_cmd(**scenario.cmd)
    result = utils.cli_cmd(cli_cmd, scenario.input_val)
    if scenario.id == "install_overwrite":
        result = utils.cli_cmd(cli_cmd, scenario.input_val)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_is_dir(LIB_DIR)
    if scenario.expected_output:
        utils.assert_in_output(scenario.expected_output, result=result)
