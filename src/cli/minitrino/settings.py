"""Settings and configuration for Minitrino CLI."""

# Docker labels
ROOT_LABEL = "org.minitrino.root=true"
MODULE_LABEL_KEY = "org.minitrino.module"
COMPOSE_LABEL_KEY = "com.docker.compose.project"

# Generic Constants
LIB = "lib"
MODULE_ROOT = "modules"
MODULE_ADMIN = "admin"
MODULE_CATALOG = "catalog"
MODULE_SECURITY = "security"
MODULE_RESOURCES = "resources"
MIN_CLUSTER_VER = 443
DEFAULT_CLUSTER_VER = 476
ETC_DIR = "/etc/${CLUSTER_DIST}"
LIC_VOLUME_MOUNT = (
    "${LIC_PATH:-./modules/resources/dummy.license}:"
    "${LIC_MOUNT_PATH:-/mnt/etc/dummy.license:ro}"
)
LIC_MOUNT_PATH = "/mnt/etc/starburstdata.license:ro"
CLUSTER_CONFIG = "config.properties"
CLUSTER_JVM_CONFIG = "jvm.config"

# Snapshots
SNAPSHOT_ROOT_FILES = [
    "docker-compose.yaml",
    "minitrino.env",
    "version",
    "image",
]

# Scrubbing
SCRUBBED = "*" * 8
SCRUB_KEYS = [
    "key",
    "-key",
    "_key",
    "password",
    "-password",
    "_password",
    "token",
    "-token",
    "_token",
]

# Templates
CONFIG_TEMPLATE = """
[config]
# defaults to ~/.minitrino/lib
LIB_PATH=

# 'trino' or 'starburst'
IMAGE=

# defaults to 'default'
CLUSTER_NAME=

# Starburst license file path
LIC_PATH=

CLUSTER_VER=
TEXT_EDITOR=
"""

# fmt: off
PROVISION_SNAPSHOT_TEMPLATE = """
#!/usr/bin/env bash

# ------------------------------------------------------------------------------------
# Below is the exact command used to provision the snapshotted environment. Run this
# command in your terminal to reproduce the exact state of the environment.
#
# If you need config data from the snapshot's 'minitrino.cfg' file, you will either
# need to copy it from the snapshot directory to '~./minitrino/minitrino.cfg' or
# individually copy the needed configs to your existing 'minitrino.cfg' file.
# ------------------------------------------------------------------------------------


"""
# fmt: on
