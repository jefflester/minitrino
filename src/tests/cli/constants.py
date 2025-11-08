"""Constants for Minitrino CLI tests."""

import os

CLUSTER_NAME = "cli-test"
CLUSTER_NAME_2 = "cli-test-2"
TEST_IMAGE_NAME = "minitrino/test:latest"
TEST_CONTAINER = "test-cli-test"
MINITRINO_CONTAINER = "minitrino-cli-test"
STOPPED_CONTAINER_MSG = "Stopped container"
REMOVED_CONTAINER_MSG = "Removed container"
IS_GITHUB = os.environ.get("IS_GITHUB", False)
