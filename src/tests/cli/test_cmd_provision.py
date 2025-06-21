from dataclasses import dataclass

import pytest
from click.testing import Result

from minitrino.settings import DEFAULT_CLUSTER_VER, ETC_DIR, MIN_CLUSTER_VER
from tests import common
from tests.cli import utils
from tests.cli.constants import (
    CLUSTER_NAME,
    MINITRINO_CONTAINER,
    TEST_CONTAINER,
)

CMD_PROVISION_MOD: common.BuildCmdArgs = {
    "base": "provision",
    "append": ["--module", "test"],
}

pytestmark = pytest.mark.usefixtures(
    "log_test", "start_docker", "down", "reset_metadata"
)
builder = common.CLICommandBuilder(utils.CLUSTER_NAME)


@pytest.fixture(autouse=True, scope="module")
def clean_before_test():
    """Clean up the env before running tests."""
    utils.shut_down()
    common.cli_cmd(
        builder.build_cmd("remove", "all", append=["--volume", "--network"]),
        log_output=False,
    )
    yield


@dataclass
class VersionScenario:
    """
    Version scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    image_type : str
        The cluster image type (trino or starburst).
    version : str
        The cluster version to test.
    expected_exit_code : int
        The expected exit code.
    expected_output : str
        The expected output string to assert.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    image_type: str
    version: str
    expected_exit_code: int
    expected_output: str
    log_msg: str


version_scenarios = [
    VersionScenario(
        id="default_version",
        image_type="",
        version="",
        expected_exit_code=0,
        expected_output="Provisioning standalone",
        log_msg="Version requirements: default version should succeed",
    ),
    VersionScenario(
        id="version_lower_bound_starburst",
        image_type="starburst",
        version=f"{MIN_CLUSTER_VER - 1}-e",
        expected_exit_code=2,
        expected_output="Provided Starburst version",
        log_msg="Version requirements: lower bound Starburst version should error",
    ),
    VersionScenario(
        id="version_lower_bound_trino",
        image_type="trino",
        version=f"{MIN_CLUSTER_VER - 1}",
        expected_exit_code=2,
        expected_output="Provided Trino version",
        log_msg="Version requirements: lower bound Trino version should error",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(version_scenarios),
    ids=utils.get_scenario_ids(version_scenarios),
    indirect=["log_msg"],
)
def test_version_scenarios(scenario: VersionScenario) -> None:
    """Run each VersionScenario."""
    append = []
    if scenario.image_type:
        append.extend(["--image", scenario.image_type])
    prepend = []
    if scenario.version:
        prepend.extend(["--env", f"CLUSTER_VER={scenario.version}"])
    cmd = builder.build_cmd(base="provision", prepend=prepend, append=append)
    result = common.cli_cmd(cmd)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_exit_code == 0 and scenario.id == "default_version":
        utils.assert_num_containers(1, all=True)
        utils.assert_containers_exist(MINITRINO_CONTAINER)
    else:
        utils.assert_num_containers(0, all=True)


@dataclass
class ModuleRequirementsScenario:
    """
    Module requirements scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    module_names : list[str]
        The module names to test.
    expected_exit_code : int
        The expected exit code.
    expected_output : str
        The expected output string to assert.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    module_names: list[str]
    expected_exit_code: int
    expected_output: str
    log_msg: str


module_requirements_scenarios = [
    ModuleRequirementsScenario(
        id="invalid_module",
        module_names=["nonexistent"],
        expected_exit_code=2,
        expected_output="Module 'nonexistent' not found",
        log_msg="Module requirements: invalid module name should error",
    ),
    ModuleRequirementsScenario(
        id="valid_module",
        module_names=["test"],
        expected_exit_code=0,
        expected_output="",
        log_msg="Module requirements: valid module name should succeed",
    ),
    ModuleRequirementsScenario(
        id="incompatible_module",
        module_names=["test", "ldap"],
        expected_exit_code=2,
        expected_output="Incompatible modules detected",
        log_msg="Module requirements: incompatible modules should error",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(module_requirements_scenarios),
    ids=utils.get_scenario_ids(module_requirements_scenarios),
    indirect=["log_msg"],
)
def test_module_requirements_scenarios(scenario: ModuleRequirementsScenario) -> None:
    """Run each ModuleRequirementsScenario."""
    append = [item for module in scenario.module_names for item in ("--module", module)]
    result = common.cli_cmd(builder.build_cmd(base="provision", append=append))
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    if scenario.expected_output:
        utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_exit_code == 0:
        utils.assert_num_containers(2, all=True)
        for module_name in scenario.module_names:
            utils.assert_containers_exist(
                MINITRINO_CONTAINER, f"{module_name}-{CLUSTER_NAME}"
            )
    else:
        utils.assert_num_containers(0, all=True)


@dataclass
class EnterpriseScenario:
    """
    Enterprise scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    enterprise : bool
        Whether the module is enterprise.
    license_path : str | None
        The path to the license file.
    expected_exit_code : int | None
        The expected exit code.
    expected_output : str
        The expected output string to assert.
    unexpected_output : str
        The unexpected output string to assert.
    log_msg : str
        The log message to display before running the test.
    """

    LIC_MSG = "You must provide a path to a Starburst license"

    id: str
    enterprise: bool
    license_path: str | None
    expected_exit_code: int | None
    expected_output: str
    unexpected_output: str
    log_msg: str


enterprise_scenarios = [
    EnterpriseScenario(
        id="enterprise_no_license",
        enterprise=True,
        license_path=None,
        expected_exit_code=2,
        expected_output=EnterpriseScenario.LIC_MSG,
        unexpected_output="",
        log_msg="Enterprise: missing license should error",
    ),
    EnterpriseScenario(
        id="enterprise_with_license",
        enterprise=True,
        license_path="/tmp/dummy.license",
        expected_exit_code=None,
        expected_output='"LIC_PATH": "/tmp/dummy.license"',
        unexpected_output=EnterpriseScenario.LIC_MSG,
        log_msg="Enterprise: with license should succeed",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(enterprise_scenarios),
    ids=utils.get_scenario_ids(enterprise_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("cleanup_config", "reset_metadata")
def test_enterprise_scenarios(scenario: EnterpriseScenario) -> None:
    """Run each EnterpriseScenario."""
    data = [{"enterprise": scenario.enterprise}]
    utils.update_metadata_json("test", data)
    if scenario.license_path:
        utils.write_file(scenario.license_path, "dummy")
    prepend = ["--env", f"CLUSTER_VER={DEFAULT_CLUSTER_VER}-e"]
    if scenario.license_path:
        prepend.extend(["--env", f"LIC_PATH={scenario.license_path}"])
    append = ["--image", "starburst", "--module", "test", "--no-rollback"]
    cmd = builder.build_cmd(base="provision", prepend=prepend, append=append)
    result = common.cli_cmd(cmd)
    if scenario.expected_exit_code is not None:
        utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    if scenario.expected_output:
        utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.unexpected_output:
        utils.assert_not_in_output(scenario.unexpected_output, result=result)


@dataclass
class ClusterDependencyScenario:
    """
    Cluster dependency scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    modules : list[str]
        The modules to provision.
    workers : int
        The number of workers to provision.
    expected_containers : int
        The expected number of containers.
    expected_output : str
        The expected output string to assert.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    modules: list[str]
    workers: int
    expected_containers: int
    expected_output: str
    log_msg: str


cluster_dependency_scenarios = [
    ClusterDependencyScenario(
        id="single_module",
        modules=["postgres"],
        workers=0,
        expected_containers=4,
        expected_output="Provisioning dependent cluster",
        log_msg="Dependency: single module, no workers",
    ),
    ClusterDependencyScenario(
        id="multiple_modules",
        modules=["postgres", "mysql"],
        workers=0,
        expected_containers=5,
        expected_output="Provisioning dependent cluster",
        log_msg="Dependency: multiple modules, no workers",
    ),
    ClusterDependencyScenario(
        id="with_workers",
        modules=["postgres"],
        workers=1,
        expected_containers=5,
        expected_output="Provisioning dependent cluster",
        log_msg="Dependency: single module with workers",
    ),
    ClusterDependencyScenario(
        id="circular_dependency",
        modules=["test"],
        workers=0,
        expected_containers=2,
        expected_output="Circular dependency detected",
        log_msg="Dependency: circular dependency should error",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(cluster_dependency_scenarios),
    ids=utils.get_scenario_ids(cluster_dependency_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.usefixtures("reset_metadata")
def test_cluster_dependency_scenarios(scenario: ClusterDependencyScenario) -> None:
    """Run each ClusterDependencyScenario."""
    if scenario.id == "circular_dependency":
        utils.update_metadata_json("test", [dep_cluster_metadata(modules=["test"])])
        expected_exit_code = 2
    else:
        utils.update_metadata_json(
            "test",
            [dep_cluster_metadata(modules=scenario.modules, workers=scenario.workers)],
        )
        expected_exit_code = 0
    cmd_args = CMD_PROVISION_MOD.copy()
    result = common.cli_cmd(builder.build_cmd(**cmd_args))
    utils.assert_exit_code(result, expected=expected_exit_code)
    utils.assert_in_output(scenario.expected_output, result=result)
    if expected_exit_code == 0:
        utils.assert_num_containers(scenario.expected_containers, all=True)
        containers = [MINITRINO_CONTAINER]
        if "postgres" in scenario.modules:
            containers.append(f"postgres-{CLUSTER_NAME}-dep-test")
        if "mysql" in scenario.modules:
            containers.append(f"mysql-{CLUSTER_NAME}-dep-test")
        if scenario.workers > 0:
            containers.append(f"minitrino-worker-1-{CLUSTER_NAME}-dep-test")
        utils.assert_containers_exist(*containers)
    else:
        utils.assert_num_containers(scenario.expected_containers)


@dataclass
class AppendConfigScenario:
    """
    Append config scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    config_type : str
        The type of config to set.
    config_value : str
        The value of the config to set.
    expected_exit_code : int
        The expected exit code.
    expected_output : str
        The expected output string to assert.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    config_type: str
    config_value: str
    expected_exit_code: int
    expected_output: str
    log_msg: str


config_scenarios = [
    AppendConfigScenario(
        id="valid_config",
        config_type="CONFIG_PROPERTIES",
        config_value="query.max-stage-count=85\nquery.max-execution-time=1h",
        expected_exit_code=0,
        expected_output="Appending user-defined config to cluster container config",
        log_msg="Config: valid config should succeed",
    ),
    AppendConfigScenario(
        id="duplicate_config",
        config_type="CONFIG_PROPERTIES",
        config_value="query.max-stage-count=85\nquery.max-stage-count=100",
        expected_exit_code=0,
        expected_output="Duplicate configuration properties detected",
        log_msg="Config: duplicate config props should warn",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(config_scenarios),
    ids=utils.get_scenario_ids(config_scenarios),
    indirect=["log_msg"],
)
def test_append_config_scenarios(scenario: AppendConfigScenario) -> None:
    """Run each AppendConfigScenario."""
    prepend = ["--env", f"{scenario.config_type}={scenario.config_value}"]
    cmd_args = CMD_PROVISION_MOD.copy()
    cmd_args["prepend"] = prepend
    result = common.cli_cmd(builder.build_cmd(**cmd_args))
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_exit_code == 0:
        utils.assert_num_containers(2, all=True)
        utils.assert_containers_exist(MINITRINO_CONTAINER, TEST_CONTAINER)


@dataclass
class ModuleAddScenario:
    """
    Module-add scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    modules_list : list[str]
        The list of modules to append.
    expected_containers : int
        The expected number of containers.
    sequential : bool
        Whether to add the modules sequentially.
    expected_output : str
        The expected output string to assert.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    modules_list: list[str]
    expected_containers: int
    sequential: bool
    expected_output: str
    log_msg: str


# TODO: Re-enable when module-add is properly implemented

module_add_scenarios = [
    ModuleAddScenario(
        id="single_module_add",
        modules_list=["test"],
        expected_containers=2,
        sequential=False,
        expected_output="",
        log_msg="Module add: single module",
    ),
    # ModuleAddScenario(
    #     id="multiple_modules_add",
    #     modules_list=["test", "postgres"],
    #     expected_containers=3,
    #     sequential=False,
    #     expected_output="",
    #     log_msg="Module add: two modules",
    # ),
    # ModuleAddScenario(
    #     id="sequential_modules_add",
    #     modules_list=["test", "postgres"],
    #     expected_containers=3,
    #     sequential=True,
    #     expected_output="Identified the following running modules",
    #     log_msg="Module add: sequential modules",
    # ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(module_add_scenarios),
    ids=utils.get_scenario_ids(module_add_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.parametrize(
    "provision_clusters",
    [{"keepalive": True}, {"no_modules": True}],
    indirect=True,
)
@pytest.mark.usefixtures("provision_clusters")
def test_module_add_scenarios(scenario: ModuleAddScenario) -> None:
    """Run each ModuleAddScenario."""
    common.cli_cmd(builder.build_cmd(base="down", cluster="all", append=["--sig-kill"]))
    if len(scenario.modules_list) == 1:
        _provision_module([scenario.modules_list[0]], scenario, is_last=True)
    elif scenario.sequential:
        for i, module in enumerate(scenario.modules_list):
            is_last = i == len(scenario.modules_list) - 1
            _provision_module([module], scenario, is_last=is_last)
    else:
        _provision_module(scenario.modules_list, scenario, is_last=True)
    _assert_catalog_files(scenario.modules_list)


def _provision_module(
    modules: list[str], scenario: ModuleAddScenario, is_last: bool
) -> None:
    module_flags = [flag for m in modules for flag in ("--module", m)]
    result = common.cli_cmd(builder.build_cmd(base="provision", append=module_flags))
    utils.assert_exit_code(result)
    if is_last:
        if scenario.expected_output:
            utils.assert_in_output(scenario.expected_output, result=result)
        utils.assert_num_containers(scenario.expected_containers)


def _assert_catalog_files(modules: list[str]) -> None:
    output = common.execute_in_coordinator(
        f"ls {ETC_DIR}/catalog/", MINITRINO_CONTAINER
    )
    for m in modules:
        if m != "test":  # Skip test module as it doesn't create catalog files
            utils.assert_in_output(f"{m}.properties", result=output)


@dataclass
class WorkerScenario:
    """
    Worker provisioning scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    workers : int
        Number of workers to provision
    expected_containers : int
        Expected number of containers
    expected_output : str
        Expected output string to assert
    log_msg : str
        Log message to display before running the test
    """

    id: str
    workers: int
    add: int
    remove: int
    expected_containers: int
    expected_container_names: list[str]
    expected_output: str
    log_msg: str


worker_scenarios = [
    WorkerScenario(
        id="single_worker",
        workers=1,
        add=0,
        remove=0,
        expected_containers=2,
        expected_output="",
        expected_container_names=["minitrino-worker-1-cli-test"],
        log_msg="Workers: single worker",
    ),
    WorkerScenario(
        id="multiple_workers",
        workers=2,
        add=0,
        remove=0,
        expected_containers=3,
        expected_output="",
        expected_container_names=["minitrino-worker-2-cli-test"],
        log_msg="Workers: multiple workers",
    ),
    WorkerScenario(
        id="add_worker",
        workers=2,
        add=1,
        remove=0,
        expected_containers=4,
        expected_output="Adding",
        expected_container_names=["minitrino-worker-3-cli-test"],
        log_msg="Workers: add worker",
    ),
    WorkerScenario(
        id="remove_worker",
        workers=2,
        add=0,
        remove=1,
        expected_containers=2,
        expected_output="Removed excess worker",
        expected_container_names=["minitrino-worker-1-cli-test"],
        log_msg="Workers: remove worker",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(worker_scenarios),
    ids=utils.get_scenario_ids(worker_scenarios),
    indirect=["log_msg"],
)
def test_worker_scenarios(
    scenario: WorkerScenario,
) -> None:
    """Run each WorkerScenario."""

    def _run_cmd(workers: int, add: int = 0, remove: int = 0) -> Result:
        common.cli_cmd(
            builder.build_cmd(base="provision", append=["--workers", str(workers)]),
        )
        return common.cli_cmd(
            builder.build_cmd(
                base="provision", append=["--workers", str(workers + add - remove)]
            ),
        )

    if scenario.add > 0:
        result = _run_cmd(scenario.workers, add=scenario.add)
    elif scenario.remove > 0:
        result = _run_cmd(scenario.workers, remove=scenario.remove)
    else:
        result = _run_cmd(scenario.workers)

    utils.assert_exit_code(result)
    utils.assert_in_output(scenario.expected_output, result=result)
    utils.assert_num_containers(scenario.expected_containers)
    utils.assert_containers_exist(*scenario.expected_container_names)


TEST_BOOTSTRAP_MSG = "Test bootstrap script execution in containers"


@pytest.mark.parametrize("log_msg", [TEST_BOOTSTRAP_MSG], indirect=True)
def test_bootstrap() -> None:
    """Ensure bootstrap scripts execute in containers."""

    cmd_args = CMD_PROVISION_MOD.copy()
    result = common.cli_cmd(builder.build_cmd(**cmd_args))
    utils.assert_exit_code(result)
    utils.assert_in_output("Successfully executed bootstrap script", result=result)

    minitrino_bootstrap_env_var = common.execute_cmd(
        "cat /tmp/bootstrap-env-var.txt", container=MINITRINO_CONTAINER
    )
    minitrino_bootstrap_before = common.execute_cmd(
        "cat /tmp/bootstrap-before.txt", container=MINITRINO_CONTAINER
    )
    minitrino_bootstrap_after = common.execute_cmd(
        "cat /tmp/bootstrap-after.txt", container=MINITRINO_CONTAINER
    )
    test_bootstrap = common.execute_cmd(
        "cat /tmp/bootstrap.txt", container=TEST_CONTAINER
    )
    utils.assert_in_output("hello world", result=test_bootstrap)
    utils.assert_in_output("hello world", result=minitrino_bootstrap_env_var)
    utils.assert_in_output("hello world", result=minitrino_bootstrap_before)
    utils.assert_in_output("hello world", result=minitrino_bootstrap_after)


TEST_VALID_USER_CONFIG_MSG = "Test valid user-defined cluster and JVM config"


@pytest.mark.parametrize("log_msg", ["test_stargate_parallel"], indirect=True)
def test_stargate_parallel() -> None:
    """Ensure valid configs can be appended to cluster config files."""
    prepend = [
        "--env",
        "cluster_ver=468-e.1",
        "--env",
        "lic_path=~/work/license/starburstdata.license",
    ]
    append = ["--module", "stargate-parallel", "--image", "starburst"]
    result = common.cli_cmd(
        builder.build_cmd(base="provision", prepend=prepend, append=append)
    )
    utils.assert_exit_code(result)


@pytest.mark.parametrize("log_msg", [TEST_VALID_USER_CONFIG_MSG], indirect=True)
def test_valid_user_config() -> None:
    """Ensure valid configs can be appended to cluster config files."""
    prepend = [
        "--env",
        "CONFIG_PROPERTIES=query.max-stage-count=85\nquery.max-execution-time=1h",
        "--env",
        "JVM_CONFIG=-Xms1G\n-Xmx2G",
    ]
    cmd_args = CMD_PROVISION_MOD.copy()
    cmd_args["prepend"] = prepend
    result = common.cli_cmd(builder.build_cmd(**cmd_args))
    utils.assert_exit_code(result)
    utils.assert_in_output("Appending user-defined config", result=result)

    config = common.execute_in_coordinator(
        f"cat {ETC_DIR}/jvm.config {ETC_DIR}/config.properties", MINITRINO_CONTAINER
    )
    utils.assert_in_output(
        "-Xms1G",
        "-Xmx2G",
        "query.max-stage-count=85",
        "query.max-execution-time=1h",
        result=config,
    )


TEST_DUPLICATE_CONFIG_PROPS_MSG = "Test duplicate configuration properties warning"


@pytest.mark.parametrize("log_msg", [TEST_DUPLICATE_CONFIG_PROPS_MSG], indirect=True)
def test_duplicate_config_props() -> None:
    """Ensure that duplicate config properties are logged as a warning
    to the user."""
    from minitrino.core.cluster.cluster import Cluster
    from minitrino.core.cluster.validator import ClusterValidator
    from minitrino.core.context import MinitrinoContext
    from minitrino.core.logging.logger import LogLevel

    ctx = MinitrinoContext()
    ctx.cluster_name = CLUSTER_NAME
    ctx._log_level = LogLevel.DEBUG

    log_output: list[str] = []
    ctx.logger.set_log_sink(log_output)

    cluster = Cluster(ctx)
    validator = ClusterValidator(ctx, cluster)

    validator.check_dup_config(
        cluster_cfgs=[
            ("key_value", "foo", "1"),
            ("key_value", "foo", "2"),
            ("unified", "foo"),
            ("unified", "foo"),
        ],
        jvm_cfgs=[
            ("unified", "-Xms1G"),
            ("unified", "-Xms1G"),
        ],
    )

    utils.assert_in_output(
        "Duplicate configuration properties detected in 'config.properties' file",
        "foo=1",
        "foo=2",
        "Duplicate configuration properties detected in 'jvm.config' file",
        "-Xms1G",
        result=log_output,
    )


def dep_cluster_metadata(name="test", modules=["postgres"], workers=0) -> dict:
    """
    Return a dictionary with dependent cluster metadata.

    Parameters
    ----------
    name : str
        Name of the dependent cluster.
    modules : list[str]
        List of modules to be provisioned in the dependent cluster.
    workers : int
        Number of workers to be provisioned in the dependent cluster.
    """
    return {
        "dependentClusters": [{"name": name, "modules": modules, "workers": workers}]
    }
