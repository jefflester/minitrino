import io
import time
from dataclasses import dataclass
from typing import Any, Optional

import pytest
from click.testing import Result
from docker import DockerClient
from docker.models.images import ImageCollection
from docker.models.networks import NetworkCollection
from docker.models.volumes import VolumeCollection

from minitrino.settings import (
    COMPOSE_LABEL_KEY,
    MODULE_LABEL_KEY,
    ROOT_LABEL,
)
from test import common
from test.cli import utils
from test.cli.constants import (
    CLUSTER_NAME,
    CLUSTER_NAME_2,
    GH_WORKFLOW_RUNNING,
    TEST_IMAGE_NAME,
)

CMD_REMOVE = {"base": "remove"}

CMD_DOWN = {"base": "down", "cluster": "all"}
CMD_DOWN_KEEP = {"base": "down", "cluster": "all", "append": ["--sig-kill", "--keep"]}

CLUSTER_LABEL = f"{COMPOSE_LABEL_KEY}=minitrino-cli-test"
TEST_MODULE_LABEL = f"{MODULE_LABEL_KEY}=catalog-test"

REMOVED_VOLUME = "Volume removed:"
REMOVED_NETWORK = "Network removed:"
REMOVED_IMAGE = "Image removed:"
FAILURE_VOLUME = "Cannot remove volume"
FAILURE_NETWORK = "Cannot remove network"


@pytest.fixture(scope="session")
def dummy_resources() -> dict:
    """
    Spin up dummy Docker resources for testing.

    Returns
    -------
    dict
        Dictionary of created resource objects.

    Notes
    -----
    Fails if resource cleanup fails. Logs resource creation and cleanup.
    """

    volume = "minitrino_dummy_volume"
    image = "minitrino_dummy_image"
    network = "minitrino_dummy_network"
    container = "minitrino_dummy_container"
    labels = {"org.minitrino": "test"}

    def _cleanup_resources(client: DockerClient):
        c = client.containers
        remove = [
            ("container", container, lambda: c.get(container).remove(force=True)),
            ("volume", volume, lambda: client.volumes.get(volume).remove(force=True)),
            ("network", network, lambda: client.networks.get(network).remove()),
            ("image", image, lambda: client.images.remove(image, force=True)),
        ]
        for resource_type, name, action in remove:
            try:
                action()
                utils.logger.debug(f"{resource_type.capitalize()} removed: {name}")
            except Exception as e:
                utils.logger.warning(
                    f"Failed to remove {resource_type} {name}: {e}"
                    "It may have already been removed."
                )

    utils.logger.debug("Starting Docker daemon for dummy resources")
    common.start_docker_daemon(utils.logger)
    client, _ = utils.docker_client()
    _cleanup_resources(client)
    resources = {}
    utils.logger.debug(f"Creating dummy volume: {volume}")
    resources["volume"] = client.volumes.create(name=volume, labels=labels)
    utils.logger.debug("Pulling busybox:latest image")
    client.images.pull("busybox:latest")
    dockerfile = "FROM busybox:latest\n\nLABEL org.minitrino=test"
    utils.logger.debug(f"Building dummy image: {image}")
    image_obj, _ = client.images.build(
        fileobj=io.BytesIO(dockerfile.encode()), tag=image, rm=True
    )
    resources["image"] = image_obj
    utils.logger.debug(f"Creating dummy network: {network}")
    resources["network"] = client.networks.create(network, labels=labels)
    utils.logger.debug(f"Creating dummy container: {container}")
    container_obj = client.containers.create(
        image=image,
        name=container,
        command="sleep 60000",
        detach=True,
        network=network,
        labels=labels,
    )
    container_obj.start()
    resources["container"] = container_obj

    yield resources
    _cleanup_resources(client)


pytestmark = pytest.mark.usefixtures(
    "log_test", "dummy_resources", "start_docker", "provision_clusters", "remove"
)


@dataclass
class RemoveAllScenario:
    """
    Remove-all scenario.

    Parameters
    ----------
    id : str
        Identifier for scenario, used in pytest parametrize ids.
    cmd_flags : Optional[list[str]]
        The command flags to use.
    expected_remove_types : list[str]
        The resource types to remove.
    label : Optional[str]
        The label to use.
    image_name : Optional[str]
        The image name to use.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    expected_remove_types: list[str]
    cmd_flags: list[str]
    label: Optional[str]
    image_name: Optional[str]
    log_msg: str


remove_all_scenarios = [
    RemoveAllScenario(
        id="images",
        cmd_flags=["--images"],
        expected_remove_types=["images"],
        label=None,
        image_name=TEST_IMAGE_NAME,
        log_msg="Remove all images",
    ),
    RemoveAllScenario(
        id="volumes",
        cmd_flags=["--volumes"],
        expected_remove_types=["volumes"],
        label=ROOT_LABEL,
        image_name=None,
        log_msg="Remove all volumes",
    ),
    RemoveAllScenario(
        id="networks",
        cmd_flags=["--networks"],
        expected_remove_types=["networks"],
        label=ROOT_LABEL,
        image_name=None,
        log_msg="Remove all networks",
    ),
    RemoveAllScenario(
        id="all_explicit",
        cmd_flags=["--images", "--volumes", "--networks"],
        expected_remove_types=["images", "volumes", "networks"],
        label=ROOT_LABEL,
        image_name=None,
        log_msg="Remove all resources (explicit)",
    ),
    RemoveAllScenario(
        id="all_implicit",
        cmd_flags=None,
        expected_remove_types=["images", "volumes", "networks"],
        label=ROOT_LABEL,
        image_name=None,
        log_msg="Remove all resources (implicit)",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(remove_all_scenarios),
    ids=utils.get_scenario_ids(remove_all_scenarios),
    indirect=["log_msg"],
)
def test_remove_all_scenarios(
    docker_client: DockerClient, scenario: RemoveAllScenario
) -> None:
    """Run each RemoveAllScenario."""

    if "images" in scenario.expected_remove_types:
        if not GH_WORKFLOW_RUNNING:
            return

    append_flags = []
    if scenario.cmd_flags:
        append_flags.extend(scenario.cmd_flags)

    result = utils.cli_cmd(
        utils.build_cmd(**CMD_REMOVE, cluster="all", append=append_flags), "y\n"
    )
    utils.assert_exit_code(result)
    assert_resources_removed(
        docker_client=docker_client,
        result=result,
        resource_types=scenario.expected_remove_types,
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
    expected_remove_types : list[str]
        The resource types to remove.
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
    expected_remove_types: list[str]
    cmd_flag: Optional[str]
    label: str
    module_flag: Optional[str]
    module_name: Optional[str]
    log_msg: str


remove_module_scenarios = [
    RemoveModuleScenario(
        id="module_volumes",
        expected_remove_types=["volumes"],
        cmd_flag="--volumes",
        label=TEST_MODULE_LABEL,
        module_flag="--module",
        module_name="test",
        log_msg="Remove module volumes",
    ),
    RemoveModuleScenario(
        id="module_networks",
        expected_remove_types=[],
        cmd_flag="--networks",
        label=TEST_MODULE_LABEL,
        module_flag="--module",
        module_name="test",
        log_msg="Networks are tied to cluster, nothing gets removed here",
    ),
    RemoveModuleScenario(
        id="module_all",
        expected_remove_types=["volumes"],
        cmd_flag=None,
        label=TEST_MODULE_LABEL,
        module_flag="--module",
        module_name="test",
        log_msg="Remove all module resources",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(remove_module_scenarios),
    ids=utils.get_scenario_ids(remove_module_scenarios),
    indirect=["log_msg"],
)
def test_remove_module_scenarios(
    docker_client: DockerClient,
    scenario: RemoveModuleScenario,
) -> None:
    """Run each RemoveModuleScenario."""
    append_flags = []
    if scenario.cmd_flag:
        append_flags.append(scenario.cmd_flag)
    if scenario.module_flag:
        append_flags.append(scenario.module_flag)
    if scenario.module_name:
        append_flags.append(scenario.module_name)
    result = utils.cli_cmd(
        utils.build_cmd(**CMD_REMOVE, cluster="all", append=append_flags),
    )
    utils.assert_exit_code(result)
    assert_resources_removed(
        docker_client=docker_client,
        result=result,
        resource_types=scenario.expected_remove_types,
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


remove_cluster_resource_scenarios = [
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


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(remove_cluster_resource_scenarios),
    ids=utils.get_scenario_ids(remove_cluster_resource_scenarios),
    indirect=["log_msg"],
)
@pytest.mark.parametrize(
    "provision_clusters",
    [{"cluster_names": [CLUSTER_NAME_2]}],
    indirect=True,
)
def test_remove_cluster_resource_scenarios(
    docker_client: DockerClient,
    scenario: RemoveClusterResourceScenario,
) -> None:
    """Run each RemoveClusterResourceScenario."""
    cmd = utils.build_cmd(
        **CMD_REMOVE, cluster=CLUSTER_NAME_2, append=scenario.cmd_flags
    )
    result = utils.cli_cmd(cmd)
    utils.assert_exit_code(result)
    for resource_type in scenario.resource_types:
        utils.assert_in_output(
            f"{resource_type[:-1].capitalize()} removed", result=result
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
class RemoveForceScenario:
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
    log_match : str
        The log message to expect.
    expected_resource_count : int
        The expected resource count.
    log_msg: str
        The log message to display before running the test.
    """

    id: str
    resource_type: str
    cmd_flag: str
    log_match: str
    expected_resource_count: int
    log_msg: str


remove_force_scenarios = [
    RemoveForceScenario(
        id="volumes_dependent_force_running",
        resource_type="volumes",
        cmd_flag="--volumes",
        log_match=FAILURE_VOLUME,
        expected_resource_count=1,
        log_msg="Force remove dependent volume from running cluster",
    ),
    RemoveForceScenario(
        id="volumes_dependent_force_stopped",
        resource_type="volumes",
        cmd_flag="--volumes",
        log_match=FAILURE_VOLUME,
        expected_resource_count=1,
        log_msg="Force remove dependent volume from stopped cluster",
    ),
    RemoveForceScenario(
        id="networks_dependent_force_running",
        resource_type="networks",
        cmd_flag="--networks",
        log_match=FAILURE_NETWORK,
        expected_resource_count=1,
        log_msg="Force remove dependent network from running cluster",
    ),
    RemoveForceScenario(
        id="networks_dependent_force_stopped",
        resource_type="networks",
        cmd_flag="--networks",
        log_match=REMOVED_NETWORK,
        expected_resource_count=0,
        log_msg="Force remove dependent network from stopped cluster",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg,provision_clusters",
    [
        (*s, {"keepalive": True})
        for s in utils.get_scenario_and_log_msg(remove_force_scenarios)
    ],
    ids=utils.get_scenario_ids(remove_force_scenarios),
    indirect=["log_msg", "provision_clusters"],
)
def test_remove_force_scenarios(
    docker_client: DockerClient,
    scenario: RemoveForceScenario,
) -> None:
    """Run each RemoveForceScenario."""
    if scenario.id.endswith("_stopped"):
        utils.cli_cmd(utils.build_cmd(**CMD_DOWN_KEEP))
    cmd = utils.build_cmd(
        **CMD_REMOVE,
        cluster="all",
        append=[scenario.cmd_flag, "--force"],
    )
    result = utils.cli_cmd(cmd)
    utils.assert_exit_code(result)
    utils.assert_in_output(scenario.log_match, result=result)
    assert_docker_resource_count(
        DockerResourceCount(
            getattr(docker_client, scenario.resource_type),
            ROOT_LABEL,
            scenario.expected_resource_count,
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
    expected_exit_code : int
        The expected exit code.
    log_msg : str
        The log message to display before running the test.
    """

    id: str
    append_flags: list[str]
    expected_msg: str
    cluster: str
    expected_exit_code: int
    log_msg: str


images_negative_scenarios = [
    RemoveImagesNegativeScenario(
        id="images_module_negative",
        append_flags=["--images", "--module", "test"],
        expected_msg="Cannot remove images for a specific module",
        cluster="all",
        expected_exit_code=2,
        log_msg="Negative: images with module",
    ),
    RemoveImagesNegativeScenario(
        id="images_cluster_negative",
        append_flags=["--images"],
        expected_msg="Cannot remove images for a specific cluster",
        cluster=CLUSTER_NAME,
        expected_exit_code=0,
        log_msg="Negative: images with specific cluster",
    ),
]


@pytest.mark.parametrize(
    "scenario,log_msg",
    utils.get_scenario_and_log_msg(images_negative_scenarios),
    ids=utils.get_scenario_ids(images_negative_scenarios),
    indirect=["log_msg"],
)
def test_remove_images_negative_scenarios(
    docker_client: DockerClient,
    scenario: RemoveImagesNegativeScenario,
) -> None:
    """Run each RemoveImagesNegativeScenario."""
    result = utils.cli_cmd(
        utils.build_cmd(
            **CMD_REMOVE, cluster=scenario.cluster, append=scenario.append_flags
        )
    )
    utils.assert_exit_code(result, scenario.expected_exit_code)
    utils.assert_in_output(scenario.expected_msg, result=result)
    assert_docker_resource_count(
        DockerResourceCount(
            docker_client.images,
            label=ROOT_LABEL,
            expected_count=1,
            image_names=[TEST_IMAGE_NAME],
        )
    )


TEST_MULTI_MOD_ALL_MSG = "Testing removing multiple modules from all clusters"


@pytest.mark.parametrize(
    "log_msg,provision_clusters",
    [(TEST_MULTI_MOD_ALL_MSG, {"modules": ["postgres"], "keepalive": True})],
    indirect=True,
)
def test_remove_multiple_module_all(
    docker_client: DockerClient,
) -> None:
    """Remove multiple modules from all clusters."""
    utils.cli_cmd(utils.build_cmd(**CMD_DOWN_KEEP))
    append = ["--module", "test", "--module", "postgres"]
    cmd = utils.build_cmd(**CMD_REMOVE, cluster="all", append=append)
    result = utils.cli_cmd(cmd)
    utils.assert_exit_code(result)
    # Can't delete volumes tied to stopped containers. Networks are
    # mapped to clusters, so they are not deleted due to the module
    # flags
    assert_docker_resource_count(
        DockerResourceCount(docker_client.volumes, CLUSTER_LABEL, 2),
        DockerResourceCount(docker_client.networks, CLUSTER_LABEL, 1),
    )
    # Both volumes are removed (one for each module), but the network
    # stays since it doesn't have a module label applied to it.
    utils.cli_cmd(utils.build_cmd(**CMD_DOWN))
    result = utils.cli_cmd(cmd)
    utils.assert_exit_code(result)
    utils.assert_in_output(REMOVED_VOLUME, result=result)
    assert_docker_resource_count(
        DockerResourceCount(docker_client.images, ROOT_LABEL, 1, [TEST_IMAGE_NAME]),
        DockerResourceCount(docker_client.volumes, CLUSTER_LABEL, 0),
        DockerResourceCount(docker_client.networks, CLUSTER_LABEL, 1),
    )


@pytest.mark.parametrize(
    "log_msg,provision_clusters",
    [
        (
            "Testing invalid module",
            {"cluster_names": [CLUSTER_NAME_2], "keepalive": True},
        )
    ],
    indirect=True,
)
def test_remove_module_invalid() -> None:
    """Try to remove an invalid module."""
    result = utils.cli_cmd(
        utils.build_cmd(**CMD_REMOVE, append=["--module", "invalid"])
    )
    utils.assert_exit_code(result, expected=2)
    utils.assert_in_output("Module 'invalid' not found", result=result)


@dataclass
class DockerResourceCount:
    """
    Dataclass for Docker resource count, filtered by label.

    Parameters
    ----------
    resource_type : DockerClient.images | DockerClient.volumes |
    DockerClient.networks
        Resource type (images, volumes, networks)
    label : str
        Label to filter by
    expected_count : int
        The expected length of the returned list
    image_names : list[str] | None
        Optional list of image names to match on (only valid for
        DockerClient.images)
    """

    resource_type: ImageCollection | VolumeCollection | NetworkCollection
    label: str
    expected_count: int = 0
    image_names: list[str] | None = None


def assert_docker_resource_count(*args: DockerResourceCount) -> None:
    """
    Assert the accuracy of the count returned from a Docker resource
    lookup.

    Parameters
    ----------
    *args : tuple of DockerResourceCount

    Notes
    -----
    Before asserting values in the supplied `DockerResourceCount`
    objects, this function will assert that there is exactly one dummy
    resource of each type with the label `"org.minitrino=test"`.
    """

    time.sleep(2)  # Avoid race condition
    client, _ = utils.docker_client()
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
