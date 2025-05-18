from logging import Logger
from dataclasses import dataclass
from pytest.mark import parametrize, usefixtures

from test.cli import utils
from test.cli.constants import CLUSTER_NAME, MINITRINO_CONTAINER

CMD_RESTART = {"base": "restart"}
CMD_PROVISION = {"base": "provision"}


@dataclass
class RestartScenario:
    """
    Restart scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    provision_args : list[str]
        Arguments to pass to the provision command.
    expected_outputs : list[str]
        List of expected output substrings after restart.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    provision_args: list[str]
    expected_outputs: list[str]
    log_msg: str


restart_scenarios = [
    RestartScenario(
        id="coordinator_only",
        provision_args=[],
        expected_outputs=[f"'{MINITRINO_CONTAINER}' restarted successfully"],
        log_msg="Restart coordinator only",
    ),
    RestartScenario(
        id="with_workers",
        provision_args=["--workers", "2"],
        expected_outputs=[
            f"'{MINITRINO_CONTAINER}' restarted successfully",
            f"'{MINITRINO_CONTAINER}-worker-2' restarted successfully.",
        ],
        log_msg="Restart with workers",
    ),
]


@parametrize(
    "scenario",
    restart_scenarios,
    ids=utils.get_scenario_ids(restart_scenarios),
)
@usefixtures("log_test", "cleanup_config", "down")
def test_restart_scenarios(
    logger: Logger,
    scenario: RestartScenario,
) -> None:
    """Run each RestartScenario."""
    cmd = utils.build_cmd(**CMD_PROVISION, append=scenario.provision_args)
    result = utils.cli_cmd(cmd, logger)
    utils.assert_exit_code(result)
    result = utils.cli_cmd(utils.build_cmd(**CMD_RESTART), logger)
    utils.assert_exit_code(result)
    for expected in scenario.expected_outputs:
        utils.assert_in_output(expected, result=result)
    utils.assert_num_containers(0)
