from logging import Logger
from typing import Optional
from dataclasses import dataclass
from pytest.mark import parametrize, usefixtures

from minitrino.settings import MODULE_ADMIN, MODULE_CATALOG, MODULE_SECURITY

from test.cli import utils

CMD_MODULES = {"base": "modules"}
CMD_PROVISION = {"base": "provision", "append": ["--module", "test"]}
CMD_DOWN = {"base": "down", "append": ["--sig-kill"]}


@dataclass
class ModuleNameScenario:
    """
    Module name scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    module_name : str
        The name of the module to test.
    type_flag : Optional[str]
        The type flag to use.
    expected_exit_code : int
        The expected exit code.
    expected_output : str
        The expected output.
    log_msg : str
        The log message.
    """

    id: str
    module_name: str
    type_flag: Optional[str]
    expected_exit_code: int
    expected_output: str
    log_msg: str


module_name_scenarios = [
    ModuleNameScenario(
        id="invalid_module",
        module_name="not-a-real-module",
        type_flag=None,
        expected_exit_code=2,
        expected_output="Module %s not found.",
        log_msg="Invalid module name should not be found",
    ),
    ModuleNameScenario(
        id="valid_module",
        module_name="test",
        type_flag=None,
        expected_exit_code=0,
        expected_output="Module: test",
        log_msg="Valid module name should print metadata",
    ),
    ModuleNameScenario(
        id="no_match",
        module_name="test",
        type_flag="admin",
        expected_exit_code=0,
        expected_output="No modules match the specified criteria",
        log_msg="No matching module for type filter",
    ),
]


@parametrize(
    "scenario",
    module_name_scenarios,
    ids=utils.get_scenario_ids(module_name_scenarios),
)
@usefixtures("log_test")
def test_module_name_scenarios(
    scenario: ModuleNameScenario,
    logger: Logger,
) -> None:
    """Run each ModuleNameScenario."""
    append = ["--module", scenario.module_name]
    if scenario.type_flag:
        append.extend(["--type", scenario.type_flag])
    result = utils.cli_cmd(utils.build_cmd(**CMD_MODULES, append=append), logger)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(
        scenario.expected_output % scenario.module_name, result=result
    )


@dataclass
class TypeScenario:
    """
    Module type scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    type_flag : str
        The type flag to use.
    validate_type : str
        The type to validate.
    log_msg : str
        The log message.
    """

    id: str
    type_flag: str
    validate_type: str
    log_msg: str


type_scenarios = [
    TypeScenario(
        id="admin_type",
        type_flag=MODULE_ADMIN,
        validate_type=MODULE_ADMIN,
        log_msg="Type filter works as expected",
    ),
    TypeScenario(
        id="catalog_type",
        type_flag=MODULE_CATALOG,
        validate_type=MODULE_CATALOG,
        log_msg="Type filter works as expected",
    ),
    TypeScenario(
        id="security_type",
        type_flag=MODULE_SECURITY,
        validate_type=MODULE_SECURITY,
        log_msg="Type filter works as expected",
    ),
]


@usefixtures("log_test")
@parametrize("scenario", type_scenarios, ids=utils.get_scenario_ids(type_scenarios))
def test_type_scenarios(scenario: TypeScenario, logger: Logger) -> None:
    """Run each TypeScenario."""
    append = ["--type", scenario.type_flag, "--json"]
    result = utils.cli_cmd(utils.build_cmd(**CMD_MODULES, append=append), logger)
    utils.assert_exit_code(result)
    types = [MODULE_ADMIN, MODULE_CATALOG, MODULE_SECURITY]
    types.remove(scenario.validate_type)
    msg = "Expected path not found in output: /src/lib/modules/%s"
    for t in types:
        assert f"/src/lib/modules/{t}" not in result.output, msg % t
    assert f"/src/lib/modules/{scenario.validate_type}" in result.output, (
        msg % scenario.validate_type
    )


ALL_MODULES_MSG = "Print all module metadata if no module name is passed"


@usefixtures("log_test")
@parametrize("log_msg", [ALL_MODULES_MSG], indirect=True)
def test_all_modules(logger: Logger) -> None:
    """
    Ensure all module metadata is printed to the console if no module name is passed.
    """
    result = utils.cli_cmd(utils.build_cmd(**CMD_MODULES), logger)
    utils.assert_exit_code(result)
    expected_fields = [
        "Description:",
        "IncompatibleModules:",
        "DependentModules:",
        "Versions:",
        "Enterprise:",
        "DependentClusters:",
    ]
    utils.assert_in_output(*expected_fields, result=result)


JSON_OUTPUT_MSG = "Output module metadata in JSON format"


@usefixtures("log_test")
@parametrize("log_msg", [JSON_OUTPUT_MSG], indirect=True)
def test_json(logger: Logger) -> None:
    """Ensure module metadata is outputted in JSON format."""
    append = ["--module", "test", "--json"]
    result = utils.cli_cmd(utils.build_cmd(**CMD_MODULES, append=append), logger)
    utils.assert_exit_code(result)
    utils.assert_in_output(f'"type": "{MODULE_CATALOG}"', result=result)
    utils.assert_in_output('"test":', result=result)


TYPE_MODULE_MISMATCH_MSG = "Type + module mismatch returns no modules found"


@usefixtures("log_test")
@parametrize("log_msg", [TYPE_MODULE_MISMATCH_MSG], indirect=True)
def test_type_module_mismatch(logger: Logger) -> None:
    """Ensure type + module mismatch returns no modules found."""
    append = ["--module", "postgres", "--type", MODULE_SECURITY]
    cmd = utils.build_cmd(**CMD_MODULES, append=append)
    result = utils.cli_cmd(cmd, logger)
    utils.assert_exit_code(result)
    utils.assert_in_output("No modules match the specified criteria", result=result)


@parametrize(
    ("log_msg", "provision_clusters"),
    [("Output metadata for running modules", {"keepalive": True})],
    indirect=True,
)
@usefixtures("log_test", "provision_clusters", "down")
def test_running(logger: Logger) -> None:
    """Ensure the `module` command can output metadata for running modules."""
    result = utils.cli_cmd(
        utils.build_cmd(**CMD_MODULES, append=["--json", "--running"]), logger
    )
    utils.assert_exit_code(result)
    utils.assert_in_output(
        f'"type": "{MODULE_CATALOG}"',
        f'"type": "{MODULE_SECURITY}"',
        "file-access-control",
        result=result,
    )


RUNNING_CLUSTER_MSG = "Output metadata for running modules in a specific cluster"


@parametrize(
    ("log_msg", "provision_clusters"),
    [(RUNNING_CLUSTER_MSG, {"keepalive": True})],
    indirect=True,
)
@usefixtures("log_test", "provision_clusters", "down")
def test_running_cluster(logger: Logger) -> None:
    """
    Ensure module metadata is outputted for running modules tied to a specific cluster.
    """
    cmd = utils.build_cmd(**CMD_MODULES, append=["--json", "--running"])
    result = utils.cli_cmd(cmd, logger)
    utils.assert_exit_code(result)
    utils.assert_in_output(
        f'"type": "{MODULE_CATALOG}"',
        f'"type": "{MODULE_SECURITY}"',
        "file-access-control",
        result=result,
    )
