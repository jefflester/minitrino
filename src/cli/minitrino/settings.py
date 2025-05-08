#!/usr/bin/env python3

# Docker labels
RESOURCE_LABEL = "org.minitrino=root"
COMPOSE_LABEL = "com.docker.compose.project"
MODULE_LABEL_KEY_ROOT = "org.minitrino.module"

# Generic Constants
IMAGE = "image"
VOLUME = "volume"
LIB = "lib"
MODULE_ROOT = "modules"
MODULE_ADMIN = "admin"
MODULE_CATALOG = "catalog"
MODULE_SECURITY = "security"
MODULE_RESOURCES = "resources"
MIN_CLUSTER_VER = 443
ETC_DIR = "/etc/${CLUSTER_DIST}"
LIC_VOLUME_MOUNT = "${LIC_PATH}:${LIC_MOUNT_PATH}"
LIC_MOUNT_PATH = f"/mnt/etc/starburstdata.license:ro"
DUMMY_LIC_MOUNT_PATH = f"/etc/starburst/dummy.license:ro"
CLUSTER_CONFIG = "config.properties"
CLUSTER_JVM_CONFIG = "jvm.config"

# Snapshots
SNAPSHOT_ROOT_FILES = [
    "docker-compose.yaml",
    "minitrino.env",
    "version",
    "image",
]

# Terminal
DEFAULT_INDENT = " " * 5

# Scrub Keys
SCRUB_KEYS = [
    "accesskey",
    "apikey",
    "secretkey",
    "-key",
    "_key",
    "password",
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

WORKER_CONFIG_PROPS = """coordinator=false
http-server.http.port=8080
discovery.uri=http://minitrino:8080
internal-communication.shared-secret=bWluaXRyaW5vUm9ja3MxNQo="""

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
