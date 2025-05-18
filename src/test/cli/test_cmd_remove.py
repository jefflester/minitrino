import os

from logging import Logger
from docker import DockerClient
from typing import Optional
from dataclasses import dataclass
from click.testing import Result
from pytest.mark import parametrize, usefixtures

from minitrino.settings import ROOT_LABEL, COMPOSE_LABEL_KEY, MODULE_LABEL_KEY

from test.cli import utils
from test.cli.utils import build_cmd
from test.cli.constants import CLUSTER_NAME, CLUSTER_NAME_2, TEST_IMAGE_NAME

CMD_REMOVE = {"base": "remove"}
CMD_DOWN_KEEP = {"base": "down", "cluster": "all", "append": ["--sig-kill", "--keep"]}

TEST_MODULE_LABEL = f"{MODULE_LABEL_KEY}=catalog-test"
GH_WORKFLOW_RUNNING = os.environ.get("GH_WORKFLOW_RUNNING", False)


@dataclass
class RemoveAllScenario:
    """
    Remove-all scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    resource_type : Optional[str]
        The resource type to remove.
    cmd_flag : Optional[str]
        The command flag to use.
    label : Optional[str]
        The label to use.
    image_name : Optional[str]
        The image name to use.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    resource_type: Optional[str]
    cmd_flag: Optional[str]
    label: Optional[str]
    image_name: Optional[str]
    log_msg: str


remove_all_scenarios = [
    RemoveAllScenario(
        id="images",
        resource_type="images",
        cmd_flag="--images",
        label=None,
        image_name=TEST_IMAGE_NAME,
        log_msg="Remove all images",
    ),
    RemoveAllScenario(
        id="volumes",
        resource_type="volumes",
        cmd_flag="--volumes",
        label=ROOT_LABEL,
        image_name=None,
        log_msg="Remove all volumes",
    ),
    RemoveAllScenario(
        id="networks",
        resource_type="networks",
        cmd_flag="--networks",
        label=ROOT_LABEL,
        image_name=None,
        log_msg="Remove all networks",
    ),
    RemoveAllScenario(
        id="all",
        resource_type=None,
        cmd_flag=None,
        label=ROOT_LABEL,
        image_name=None,
        log_msg="Remove all resources",
    ),
]


@parametrize(
    "scenario",
    remove_all_scenarios,
    ids=utils.get_scenario_ids(remove_all_scenarios),
    indirect=False,
)
@usefixtures("log_test", "dummy_resources", "provision_cluster", "remove")
def test_remove_all_scenarios(
    docker_client: DockerClient,
    scenario: RemoveAllScenario,
    logger: Logger,
) -> None:
    """Run each RemoveAllScenario."""

    resource_types = (
        [scenario.resource_type]
        if scenario.resource_type
        else ["images", "volumes", "networks"]
    )

    if "images" in resource_types:
        if not GH_WORKFLOW_RUNNING:
            return

    append_flags = []
    if scenario.cmd_flag:
        append_flags.append(scenario.cmd_flag)

    result = utils.cli_cmd(
        build_cmd(**CMD_REMOVE, cluster="all", append=append_flags), logger, "y\n"
    )
    utils.assert_exit_code(result)
    assert_resources_removed(
        docker_client=docker_client,
        result=result,
        resource_types=resource_types,
        label=scenario.label,
        image_name=scenario.image_name,
    )


@dataclass
class RemoveModuleScenario:
    """
    Remove module scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    resource_type : Optional[str]
        The resource type to remove.
    cmd_flag : Optional[str]
        The command flag to use.
    label : str
        The label to use.
    module_flag : Optional[str]
        The module flag to use.
    module_name : Optional[str]
        The module name to use.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    resource_type: Optional[str]
    cmd_flag: Optional[str]
    label: str
    module_flag: Optional[str]
    module_name: Optional[str]
    log_msg: str


remove_module_scenarios = [
    RemoveModuleScenario(
        id="module_volumes",
        resource_type="volumes",
        cmd_flag="--volumes",
        label=TEST_MODULE_LABEL,
        module_flag="--module",
        module_name="test",
        log_msg="Remove module volumes",
    ),
    RemoveModuleScenario(
        id="module_networks",
        resource_type="networks",
        cmd_flag="--networks",
        label=TEST_MODULE_LABEL,
        module_flag="--module",
        module_name="test",
        log_msg="Remove module networks",
    ),
    RemoveModuleScenario(
        id="module_all",
        resource_type=None,
        cmd_flag=None,
        label=TEST_MODULE_LABEL,
        module_flag="--module",
        module_name="test",
        log_msg="Remove all module resources",
    ),
]


@parametrize(
    "scenario",
    remove_module_scenarios,
    ids=utils.get_scenario_ids(remove_module_scenarios),
    indirect=False,
)
@usefixtures("log_test", "dummy_resources", "provision_cluster", "remove")
def test_remove_module_scenarios(
    docker_client: DockerClient,
    scenario: RemoveModuleScenario,
    logger: Logger,
) -> None:
    """Run each RemoveModuleScenario."""
    resource_types = (
        [scenario.resource_type] if scenario.resource_type else ["volumes", "networks"]
    )
    append_flags = []
    if scenario.cmd_flag:
        append_flags.append(scenario.cmd_flag)
    if scenario.module_flag:
        append_flags.append(scenario.module_flag)
    if scenario.module_name:
        append_flags.append(scenario.module_name)
    result = utils.cli_cmd(
        build_cmd(**CMD_REMOVE, cluster="all", append=append_flags),
        logger,
    )
    utils.assert_exit_code(result)
    assert_resources_removed(
        docker_client=docker_client,
        result=result,
        resource_types=resource_types,
        label=scenario.label,
    )


@dataclass
class RemoveClusterResourceScenario:
    """
    Remove cluster resource scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    resource_types : list[str]
        The resource types to remove.
    cmd_flags : list[str]
        The command flags to use.
    label1 : str
        The label for the first cluster.
    label2 : str
        The label for the second cluster.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    resource_types: list[str]
    cmd_flags: list[str]
    label1: str
    label2: str
    log_msg: str


resource_cluster_scenarios = [
    RemoveClusterResourceScenario(
        id="cluster_volumes",
        resource_types=["volumes"],
        cmd_flags=["--volumes"],
        label1=f"{COMPOSE_LABEL_KEY}=minitrino-{CLUSTER_NAME}",
        label2=f"{COMPOSE_LABEL_KEY}=minitrino-{CLUSTER_NAME_2}",
        log_msg="Remove cluster volumes",
    ),
    RemoveClusterResourceScenario(
        id="cluster_networks",
        resource_types=["networks"],
        cmd_flags=["--networks"],
        label1=f"{COMPOSE_LABEL_KEY}=minitrino-{CLUSTER_NAME}",
        label2=f"{COMPOSE_LABEL_KEY}=minitrino-{CLUSTER_NAME_2}",
        log_msg="Remove cluster networks",
    ),
    RemoveClusterResourceScenario(
        id="cluster_all",
        resource_types=["volumes", "networks"],
        cmd_flags=["--volumes", "--networks"],
        label1=f"{COMPOSE_LABEL_KEY}=minitrino-{CLUSTER_NAME}",
        label2=f"{COMPOSE_LABEL_KEY}=minitrino-{CLUSTER_NAME_2}",
        log_msg="Remove all cluster resources (volumes and networks)",
    ),
]


@parametrize(
    "scenario",
    resource_cluster_scenarios,
    ids=utils.get_scenario_ids(resource_cluster_scenarios),
    indirect=False,
)
@usefixtures("log_test", "dummy_resources", "provision_two_clusters", "remove")
def test_remove_cluster_resource_scenarios(
    docker_client: DockerClient,
    scenario: RemoveClusterResourceScenario,
    logger: Logger,
) -> None:
    """Run each RemoveClusterResourceScenario."""
    cmd = build_cmd(**CMD_REMOVE, cluster=CLUSTER_NAME_2, append=scenario.cmd_flags)
    result = utils.cli_cmd(cmd, logger)
    utils.assert_exit_code(result)
    for resource_type in scenario.resource_types:
        utils.assert_in_output(
            f"{resource_type[:-1].capitalize()} removed:", result=result
        )
        assert_docker_resource_count(
            DockerResourceCount(
                getattr(docker_client, resource_type), scenario.label1, 1
            ),
            DockerResourceCount(
                getattr(docker_client, resource_type), scenario.label2, 0
            ),
        )


@dataclass
class RemoveDependentResourceForceScenario:
    """
    Remove dependent resources via force scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    resource_type : str
        The resource type to remove.
    cmd_flag : str
        The command flag to use.
    fail_msg : str
        The failure message to expect.
    success_msg : str
        The success message to expect.
    log_msg: str
        The log message to display before running the test.
    """

    id: str
    resource_type: str
    cmd_flag: str
    fail_msg: str
    success_msg: str
    log_msg: str


resource_dependent_force_scenarios = [
    RemoveDependentResourceForceScenario(
        id="volumes_dependent_force",
        resource_type="volumes",
        cmd_flag="--volumes",
        fail_msg="Cannot remove volume",
        success_msg="Volume removed:",
        log_msg="Force remove dependent volume",
    ),
    RemoveDependentResourceForceScenario(
        id="networks_dependent_force",
        resource_type="networks",
        cmd_flag="--networks",
        fail_msg="Cannot remove network",
        success_msg="Network removed:",
        log_msg="Force remove dependent network",
    ),
]


@parametrize(
    "scenario",
    resource_dependent_force_scenarios,
    ids=utils.get_scenario_ids(resource_dependent_force_scenarios),
    indirect=False,
)
@usefixtures("log_test", "dummy_resources", "provision_cluster", "remove")
def test_remove_dependent_and_force_scenarios(
    docker_client: DockerClient,
    scenario: RemoveDependentResourceForceScenario,
    logger: Logger,
) -> None:
    """Run each RemoveDependentResourceForceScenario."""
    utils.cli_cmd(build_cmd(**CMD_DOWN_KEEP), logger)
    result = utils.cli_cmd(build_cmd(**CMD_REMOVE, append=[scenario.cmd_flag]), logger)
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(scenario.fail_msg, result=result)

    result_force = utils.cli_cmd(
        build_cmd(
            **CMD_REMOVE,
            cluster="all",
            append=[scenario.cmd_flag, "--force"],
        ),
        logger,
    )
    utils.assert_exit_code(result_force)
    utils.assert_in_output(scenario.success_msg, result=result_force)
    assert_docker_resource_count(
        DockerResourceCount(
            getattr(docker_client, scenario.resource_type), ROOT_LABEL, 0
        )
    )


@dataclass
class RemoveImagesNegativeScenario:
    """
    Remove images (negative) scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    append_flags : list[str]
        The append flags to use.
    expected_msg : str
        The expected message.
    cluster : str
        The cluster to use.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    append_flags: list[str]
    expected_msg: str
    cluster: str
    log_msg: str


images_negative_scenarios = [
    RemoveImagesNegativeScenario(
        id="images_module_negative",
        append_flags=["--images", "--module", "test"],
        expected_msg="Cannot remove images for a specific module",
        cluster="all",
        log_msg="Negative: images with module",
    ),
    RemoveImagesNegativeScenario(
        id="images_cluster_negative",
        append_flags=["--images"],
        expected_msg="Cannot remove images for a specific cluster",
        cluster=CLUSTER_NAME,
        log_msg="Negative: images with specific cluster",
    ),
]


@parametrize(
    "scenario",
    images_negative_scenarios,
    ids=utils.get_scenario_ids(images_negative_scenarios),
    indirect=False,
)
@usefixtures("log_test", "dummy_resources", "provision_cluster", "remove")
def test_remove_images_negative_scenarios(
    docker_client: DockerClient,
    scenario: RemoveImagesNegativeScenario,
    logger: Logger,
) -> None:
    """Run each RemoveImagesNegativeScenario."""
    result = utils.cli_cmd(
        build_cmd(**CMD_REMOVE, cluster=scenario.cluster, append=scenario.append_flags),
        logger,
    )
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output(scenario.expected_msg, result=result)
    assert_docker_resource_count(
        DockerResourceCount(
            docker_client.images, expected_count=1, image_names=[TEST_IMAGE_NAME]
        )
    )


TEST_MULTI_MOD_ALL_MSG = "Testing removing multiple modules from all clusters"


@parametrize("log_msg", [TEST_MULTI_MOD_ALL_MSG], indirect=True)
@usefixtures("log_test", "dummy_resources", "provision_two_clusters", "remove")
def test_remove_multiple_module_all(
    docker_client: DockerClient, logger: Logger
) -> None:
    """Remove multiple modules from all clusters."""
    result = utils.cli_cmd(
        build_cmd(
            **CMD_REMOVE,
            cluster="all",
            append=["--module", "test", "--module", "postgres"],
        ),
        logger,
    )
    postgres_module_label = f"{MODULE_LABEL_KEY}=catalog-postgres"
    utils.assert_exit_code(result)
    utils.assert_in_output("Volume removed:", "Network removed:", result=result)
    assert_docker_resource_count(
        DockerResourceCount(
            docker_client.images, expected_count=1, image_names=[TEST_IMAGE_NAME]
        ),
        DockerResourceCount(docker_client.volumes, TEST_MODULE_LABEL, 0),
        DockerResourceCount(docker_client.networks, TEST_MODULE_LABEL, 0),
        DockerResourceCount(docker_client.volumes, postgres_module_label, 0),
        DockerResourceCount(docker_client.networks, postgres_module_label, 0),
    )


@parametrize("log_msg", ["Testing invalid module"], indirect=True)
@usefixtures("log_test", "dummy_resources", "provision_two_clusters", "remove")
def test_remove_module_invalid(logger: Logger) -> None:
    """Try to remove an invalid module."""
    result = utils.cli_cmd(
        build_cmd(**CMD_REMOVE, append=["--module", "invalid"]), logger
    )
    utils.assert_exit_code(result, expected_code=2)
    utils.assert_in_output("Module 'invalid' not found", result=result)


@dataclass
class DockerResourceCount:
    """
    Dataclass for Docker resource count, filtered by label.

    Parameters
    ----------
    resource_type : DockerClient.images | DockerClient.volumes | DockerClient.networks
        Resource type (images, volumes, networks)
    label : str
        Label to filter by
    expected_count : int
        The expected length of the returned list
    image_names : list[str] | None
        Optional list of image names to match on (only valid for DockerClient.images)
    """

    resource_type: DockerClient.images | DockerClient.volumes | DockerClient.networks
    label: str
    expected_count: int = 0
    image_names: list[str] | None = None


def assert_docker_resource_count(*args: DockerResourceCount) -> None:
    """
    Assert the accuracy of the count returned from a Docker resource lookup.

    Parameters
    ----------
    *args : tuple of DockerResourceCount

    Notes
    -----
    Before asserting values in the supplied `DockerResourceCount` objects, this function
    will assert that there is exactly one dummy resource of each type with the label
    `"org.minitrino=test"`.
    """

    client = DockerClient.from_env()
    label = "org.minitrino=test"
    resources = [
        ("image", client.images.list(filters={"label": label})),
        ("volume", client.volumes.list(filters={"label": label})),
        ("network", client.networks.list(filters={"label": label})),
        ("container", client.containers.list(filters={"label": label})),
    ]
    for resource_type, resource_list in resources:
        actual = len(resource_list)
        assert (
            actual == 1
        ), f"Unexpected number of dummy {resource_type}s found: {actual} (expected 1)"

    for resource in args:
        resource_list = resource.resource_type.list(filters={"label": resource.label})
        resource_type_str = (
            type(resource.resource_type).__name__.replace("Collection", "").lower()
        )
        if resource.image_names is not None:
            if resource_type_str != "image":
                raise ValueError(
                    "image_names can only be used with DockerClient.images"
                )
            all_image_names = set()
            for image in resource_list:
                all_image_names.update(image.tags)
            missing = [
                name for name in resource.image_names if name not in all_image_names
            ]
            assert not missing, (
                f"Missing expected image(s) with label {resource.label}: {missing}. "
                f"Found: {sorted(all_image_names)}"
            )
        else:
            assert len(resource_list) == resource.expected_count, (
                f"Expected {resource.expected_count} {resource_type_str}s with label "
                f"{resource.label}, but found {len(resource_list)}"
            )


def assert_resources_removed(
    docker_client: DockerClient, result: Result, **kwargs: dict[str, Any]
) -> None:
    """Assert that all specified resource types have been removed."""
    for resource_type in kwargs.get("resource_types", []):
        utils.assert_in_output(
            f"{resource_type[:-1].capitalize()} removed:", result=result
        )
        assert_docker_resource_count(
            DockerResourceCount(
                getattr(docker_client, resource_type),
                kwargs.get("label"),
                0,
                kwargs.get("image_name"),
            )
        )
