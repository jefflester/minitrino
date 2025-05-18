import yaml

from logging import Logger
from dataclasses import dataclass
from pytest.mark import parametrize, usefixtures
from minitrino.settings import MIN_CLUSTER_VER

from test import common
from test.cli import utils
from test.cli.constants import CLUSTER_NAME, MINITRINO_CONTAINER, TEST_CONTAINER

CMD_PROVISION = {"base": "provision"}
CMD_PROVISION_MOD = {"base": "provision", "append": ["--module", "test"]}


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
    VersionScenario(
        id="standalone",
        image_type="",
        version="",
        expected_exit_code=0,
        expected_output="Provisioning standalone",
        log_msg="Version requirements: standalone should succeed",
    ),
]


@parametrize(
    "scenario",
    version_scenarios,
    ids=utils.get_scenario_ids(version_scenarios),
    indirect=False,
)
@usefixtures("log_test", "down")
def test_version_scenarios(
    scenario: VersionScenario,
    logger: Logger,
) -> None:
    """Run each VersionScenario."""
    append = []
    if scenario.image_type:
        append.extend(["--type", scenario.image_type])
    prepend = []
    if scenario.version:
        prepend.extend(["--env", f"CLUSTER_VER={scenario.version}"])
    cmd = utils.build_cmd(**CMD_PROVISION, prepend=prepend, append=append)
    result = utils.cli_cmd(cmd, logger)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_exit_code == 0:
        utils.assert_num_containers(1, all=True)
        utils.assert_containers_exist("minitrino-default")
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
        expected_output="Invalid module",
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


@parametrize(
    "scenario",
    module_requirements_scenarios,
    ids=utils.get_scenario_ids(module_requirements_scenarios),
    indirect=False,
)
@usefixtures("log_test", "down")
def test_module_requirements_scenarios(
    scenario: ModuleRequirementsScenario,
    logger: Logger,
) -> None:
    """Run each ModuleRequirementsScenario."""
    append = [item for module in scenario.module_names for item in ("--module", module)]
    result = utils.cli_cmd(utils.build_cmd(**CMD_PROVISION, append=append), logger)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    if scenario.expected_output:
        utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_exit_code == 0:
        utils.assert_num_containers(2, all=True)
        for module_name in scenario.module_names:
            utils.assert_containers_exist("minitrino-default", f"{module_name}-default")
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
    module_name : str
        The module name to test.
    license_path : str | None
        The path to the license file.
    expected_exit_code : int
        The expected exit code.
    expected_output : str
        The expected output string to assert.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    enterprise: bool
    module_name: str
    license_path: str | None
    expected_exit_code: int
    expected_output: str
    log_msg: str


enterprise_scenarios = [
    EnterpriseScenario(
        id="enterprise_no_license",
        enterprise=True,
        module_name="test",
        license_path=None,
        expected_exit_code=2,
        expected_output="You must provide a path to a Starburst license",
        log_msg="Enterprise: missing license should error",
    ),
    EnterpriseScenario(
        id="enterprise_with_license",
        enterprise=True,
        module_name="test",
        license_path="/tmp/dummy.license",
        expected_exit_code=0,
        expected_output="LIC_PATH",
        log_msg="Enterprise: with license should succeed",
    ),
]


@parametrize(
    "scenario",
    enterprise_scenarios,
    ids=utils.get_scenario_ids(enterprise_scenarios),
    indirect=False,
)
@usefixtures("log_test", "down", "reset_metadata")
def test_enterprise_scenarios(
    scenario: EnterpriseScenario,
    logger: Logger,
) -> None:
    """Run each EnterpriseScenario."""
    data = [{"enterprise": scenario.enterprise}]
    utils.update_metadata_json(scenario.module_name, data)
    if scenario.license_path:
        utils.write_file(scenario.license_path, "dummy")
    prepend = (
        ["--env", f"LIC_PATH={scenario.license_path}"] if scenario.license_path else []
    )
    append = ["--module", scenario.module_name, "--no-rollback"]
    cmd = utils.build_cmd(**CMD_PROVISION, prepend=prepend, append=append)
    result = utils.cli_cmd(cmd, logger)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(scenario.expected_output, result=result)


@dataclass
class DependencyScenario:
    """
    Dependency scenario.

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


dependency_scenarios = [
    DependencyScenario(
        id="single_module",
        modules=["postgres"],
        workers=0,
        expected_containers=4,
        expected_output="Provisioning dependent cluster",
        log_msg="Dependency: single module, no workers",
    ),
    DependencyScenario(
        id="multiple_modules",
        modules=["postgres", "mysql"],
        workers=0,
        expected_containers=5,
        expected_output="Provisioning dependent cluster",
        log_msg="Dependency: multiple modules, no workers",
    ),
    DependencyScenario(
        id="with_workers",
        modules=["postgres"],
        workers=1,
        expected_containers=5,
        expected_output="Provisioning dependent cluster",
        log_msg="Dependency: single module with workers",
    ),
    DependencyScenario(
        id="circular_dependency",
        modules=["test"],
        workers=0,
        expected_containers=1,
        expected_output="Circular dependency detected",
        log_msg="Dependency: circular dependency should error",
    ),
]


@parametrize(
    "scenario",
    dependency_scenarios,
    ids=utils.get_scenario_ids(dependency_scenarios),
    indirect=False,
)
@usefixtures("log_test", "down", "reset_metadata")
def test_dependency_scenarios(
    scenario: DependencyScenario,
    logger: Logger,
) -> None:
    """Run each DependencyScenario."""
    if scenario.expected_output == "Circular dependency detected":
        utils.update_metadata_json("test", [dep_cluster_metadata("test", ["test"])])
        expected_exit_code = 1
    else:
        utils.update_metadata_json(
            "test",
            [dep_cluster_metadata(modules=scenario.modules, workers=scenario.workers)],
        )
        expected_exit_code = 0
    result = utils.cli_cmd(utils.build_cmd(**CMD_PROVISION_MOD), logger)
    utils.assert_exit_code(result, expected=expected_exit_code)
    utils.assert_in_output(scenario.expected_output, result=result)
    if expected_exit_code == 0:
        utils.assert_num_containers(scenario.expected_containers, all=True)
        containers = [MINITRINO_CONTAINER]
        if "postgres" in scenario.modules:
            containers.append(f"postgres-{CLUSTER_NAME}")
        if "mysql" in scenario.modules:
            containers.append(f"mysql-{CLUSTER_NAME}")
        if scenario.workers > 0:
            containers.append(f"{MINITRINO_CONTAINER}-worker-1")
        utils.assert_containers_exist(*containers)
    else:
        utils.assert_num_containers(0, all=True)


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


@parametrize(
    "scenario",
    config_scenarios,
    ids=utils.get_scenario_ids(config_scenarios),
    indirect=False,
)
@usefixtures("log_test", "down")
def test_append_config_scenarios(
    scenario: AppendConfigScenario,
    logger: Logger,
) -> None:
    """Run each AppendConfigScenario."""
    prepend = ["--env", f"{scenario.config_type}={scenario.config_value}"]
    result = utils.cli_cmd(
        utils.build_cmd(**CMD_PROVISION_MOD, prepend=prepend), logger
    )
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_exit_code == 0:
        utils.assert_num_containers(2, all=True)
        utils.assert_containers_exist(MINITRINO_CONTAINER, TEST_CONTAINER)


@dataclass
class DockerNativeScenario:
    """
    Native Docker flag scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    docker_native : str
        The docker native option to use.
    expected_output : str
        The expected output string to assert.
    expected_containers : int
        The expected number of containers.
    expected_exit_code : int
        The expected exit code.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    docker_native: str
    expected_output: str
    expected_containers: int
    expected_exit_code: int
    log_msg: str


docker_native_scenarios = [
    DockerNativeScenario(
        id="valid_docker_native_build",
        docker_native="--build",
        expected_output="Received native Docker Compose options",
        expected_containers=2,
        expected_exit_code=0,
        log_msg="Docker native: valid docker native should succeed",
    ),
    DockerNativeScenario(
        id="valid_docker_native_dry_run",
        docker_native="--dry-run",
        expected_output="Received native Docker Compose options",
        expected_containers=2,
        expected_exit_code=0,
        log_msg="Docker native: valid docker native should succeed",
    ),
    DockerNativeScenario(
        id="invalid_docker_native",
        docker_native="--foo-bar",
        expected_output="Received native Docker Compose options",
        expected_containers=0,
        expected_exit_code=2,
        log_msg="Docker native: invalid docker native should fail",
    ),
]


@parametrize(
    "scenario",
    docker_native_scenarios,
    ids=utils.get_scenario_ids(docker_native_scenarios),
    indirect=False,
)
@usefixtures("log_test", "down")
def test_docker_native_scenarios(
    scenario: DockerNativeScenario, logger: Logger
) -> None:
    """Run each DockerNativeScenario."""
    append = ["--module", "test", "--docker-native", scenario.docker_native]
    result = utils.cli_cmd(utils.build_cmd(**CMD_PROVISION, append=append), logger)
    utils.assert_exit_code(result, expected=scenario.expected_exit_code)
    utils.assert_in_output(scenario.expected_output, result=result)
    if scenario.expected_exit_code == 0:
        utils.assert_num_containers(scenario.expected_containers, all=True)
        utils.assert_containers_exist(MINITRINO_CONTAINER, TEST_CONTAINER)
    else:
        utils.assert_num_containers(0, all=True)


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


module_add_scenarios = [
    ModuleAddScenario(
        id="single_module_add",
        modules_list=["test"],
        expected_containers=2,
        sequential=False,
        expected_output="",
        log_msg="Module add: single module",
    ),
    ModuleAddScenario(
        id="multiple_modules_add",
        modules_list=["test", "postgres"],
        expected_containers=3,
        sequential=False,
        expected_output="Identified the following running modules",
        log_msg="Module add: two modules",
    ),
    ModuleAddScenario(
        id="sequential_modules_add",
        modules_list=["test", "postgres"],
        expected_containers=3,
        sequential=True,
        expected_output="Identified the following running modules",
        log_msg="Module add: sequential modules",
    ),
]


@parametrize(
    "scenario",
    module_add_scenarios,
    ids=utils.get_scenario_ids(module_add_scenarios),
    indirect=False,
)
@parametrize(
    "provision_clusters",
    [{"keepalive": True}, {"no_modules": True}],
    indirect=True,
)
@usefixtures("log_test", "provision_clusters", "down")
def test_module_add_scenarios(
    scenario: ModuleAddScenario,
    logger: Logger,
) -> None:
    """Run each ModuleAddScenario."""
    if len(scenario.modules_list) == 1:
        pass
    elif scenario.sequential:
        for module in scenario.modules_list:
            _provision_module([module], scenario, logger)
    else:
        _provision_module(scenario.modules_list, scenario, logger)
    _assert_catalog_files(scenario.modules_list)


def _provision_module(modules, scenario, logger):
    module_flags = [flag for m in modules for flag in ("--module", m)]
    result = utils.cli_cmd(
        utils.build_cmd(**CMD_PROVISION, append=module_flags), logger
    )
    utils.assert_exit_code(result)
    if scenario.expected_output:
        utils.assert_in_output(scenario.expected_output, result=result)
    utils.assert_num_containers(scenario.expected_containers)


def _assert_catalog_files(modules):
    etc_ls = common.execute_cmd(
        "docker exec -i minitrino-default ls /etc/${CLUSTER_DIST}/catalog/"
    )
    for m in modules:
        if m != "test":  # Skip test module as it doesn't create catalog files
            utils.assert_in_output(f"{m}.properties", result=etc_ls)


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
    expected_containers: int
    expected_output: str
    log_msg: str


worker_scenarios = [
    WorkerScenario(
        id="single_worker",
        workers=1,
        expected_containers=2,
        expected_output="started worker container: 'minitrino-worker-1'",
        log_msg="Workers: single worker",
    ),
    WorkerScenario(
        id="multiple_workers",
        workers=2,
        expected_containers=3,
        expected_output="started worker container: 'minitrino-worker-2'",
        log_msg="Workers: multiple workers",
    ),
    WorkerScenario(
        id="downsize_workers",
        workers=1,
        expected_containers=2,
        expected_output="Removed excess worker",
        log_msg="Workers: downsize workers",
    ),
]


@parametrize(
    "scenario",
    worker_scenarios,
    ids=utils.get_scenario_ids(worker_scenarios),
    indirect=False,
)
@usefixtures("log_test", "down")
def test_worker_scenarios(
    scenario: WorkerScenario,
    logger: Logger,
) -> None:
    """Run each WorkerScenario."""
    result = utils.cli_cmd(
        utils.build_cmd(**CMD_PROVISION, append=["--workers", str(scenario.workers)]),
        logger,
    )
    utils.assert_exit_code(result)
    utils.assert_in_output(scenario.expected_output, result=result)
    utils.assert_num_containers(scenario.expected_containers)

    if scenario.workers > 0:
        result = utils.cli_cmd(utils.build_cmd(**CMD_PROVISION_MOD), logger)
        utils.assert_exit_code(result)
        utils.assert_in_output(
            "Restarting container 'minitrino-worker-1'", result=result
        )
        utils.assert_num_containers(scenario.expected_containers + 1)


TEST_BOOTSTRAP_MSG = "Test bootstrap script execution in containers"


@usefixtures("log_test", "down")
@parametrize("log_msg", [TEST_BOOTSTRAP_MSG], indirect=True)
def test_bootstrap(logger: Logger) -> None:
    """Ensure bootstrap scripts execute in containers."""

    def add_yaml_bootstrap(yaml_path):
        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)
        for svc_name, svc_content in data.get("services", {}).items():
            if "environment" not in svc_content:
                svc_content["environment"] = {
                    "MINITRINO_BOOTSTRAP": f"bootstrap-{svc_name}.sh"
                }
        with open(yaml_path, "w") as file:
            yaml.dump(data, file, default_flow_style=False)

    def del_yaml_bootstrap(yaml_path):
        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)
        for _, svc_content in data.get("services", {}).items():
            if "environment" in svc_content:
                del svc_content["environment"]
        with open(yaml_path, "w") as file:
            yaml.dump(data, file, default_flow_style=False)

    yaml_path = utils.get_module_yaml_path("test")
    add_yaml_bootstrap(yaml_path)
    utils.cli_cmd(utils.build_cmd(**CMD_PROVISION_MOD), logger)
    utils.assert_exit_code(result)
    utils.assert_in_output(
        "Successfully executed bootstrap script in container 'minitrino'",
        "Successfully executed bootstrap script in container 'test'",
        result=result,
    )
    minitrino_bootstrap = common.execute_cmd(
        "docker exec -i minitrino cat /tmp/bootstrap.txt"
    )
    test_bootstrap = common.execute_cmd("docker exec -i test cat /tmp/bootstrap.txt")
    utils.assert_in_output("hello world", result=minitrino_bootstrap)
    utils.assert_in_output("hello world", result=test_bootstrap)
    del_yaml_bootstrap(yaml_path)


TEST_VALID_USER_CONFIG_MSG = "Test valid user-defined cluster and JVM config"


@usefixtures("log_test", "down")
@parametrize("log_msg", [TEST_VALID_USER_CONFIG_MSG], indirect=True)
def test_valid_user_config(logger: Logger) -> None:
    """Ensure valid configs can be appended to cluster config files."""
    prepend = [
        "--env",
        "CONFIG_PROPERTIES=query.max-stage-count=85\nquery.max-execution-time=1h",
        "--env",
        "JVM_CONFIG=-Xms1G\n-Xmx2G",
    ]
    built_cmd = utils.build_cmd(**CMD_PROVISION_MOD, prepend=prepend)
    result = utils.cli_cmd(built_cmd, logger)
    utils.assert_exit_code(result)
    utils.assert_in_output("Appending user-defined config", result=result)

    cmd = "docker exec -i minitrino cat /etc/${CLUSTER_DIST}"
    jvm_config = common.execute_cmd(f"{cmd}/jvm.config")
    cluster_config = common.execute_cmd(f"{cmd}/config.properties")
    utils.assert_in_output("-Xms1G", "-Xmx2G", result=jvm_config)
    utils.assert_in_output(
        "query.max-stage-count=85", "query.max-execution-time=1h", result=cluster_config
    )


TEST_DUPLICATE_CONFIG_PROPS_MSG = "Test duplicate configuration properties warning"


@usefixtures("log_test", "down")
@parametrize("log_msg", [TEST_DUPLICATE_CONFIG_PROPS_MSG], indirect=True)
def test_duplicate_config_props(logger: Logger) -> None:
    """Ensure that duplicate config properties are logged as a warning to the user."""
    prepend = [
        "--env",
        "CLUSTER_VER=3.2.0",
        "--env",
        "CONFIG_PROPERTIES=query.max-stage-count=85\nquery.max-stage-count=100",
        "--env",
        "JVM_CONFIG=-Xms1G\n-Xms1G",
    ]
    built_cmd = utils.build_cmd(**CMD_PROVISION, prepend=prepend)
    result = utils.cli_cmd(built_cmd, logger)
    utils.assert_exit_code(result)
    utils.assert_in_output(
        "Duplicate configuration properties detected in 'config.properties' file",
        "query.max-stage-count=85",
        "query.max-stage-count=100",
        "Duplicate configuration properties detected in 'jvm.config' file",
        "-Xms1G",
        result=result,
    )
    utils.assert_exit_code(result)


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
