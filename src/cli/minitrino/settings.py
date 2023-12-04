#!usr/bin/env/python3
# -*- coding: utf-8 -*-

# Docker labels
RESOURCE_LABEL = "com.starburst.tests=minitrino"
MODULE_LABEL_KEY_ROOT = "com.starburst.tests.module"

# Generic Constants
CONTAINER = "container"
IMAGE = "image"
VOLUME = "volume"
LIB = "lib"
MODULE_ROOT = "modules"
MODULE_ADMIN = "admin"
MODULE_CATALOG = "catalog"
MODULE_SECURITY = "security"
MODULE_RESOURCES = "resources"
MIN_SEP_VER = 402
ETC_TRINO = "/etc/starburst"
LIC_VOLUME_MOUNT = "${LIC_PATH}:${LIC_MOUNT_PATH}"
LIC_MOUNT_PATH = "/etc/starburst/starburstdata.license:ro"
DUMMY_LIC_MOUNT_PATH = "/etc/starburst/dummy.license:ro"
TRINO_CONFIG = "config.properties"
TRINO_JVM_CONFIG = "jvm.config"
LIB_INDEPENDENT_CMDS = ["lib-install"]

# Snapshots
SNAPSHOT_ROOT_FILES = [
    "docker-compose.yml",
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

STARBURST_VER=
TEXT_EDITOR=
LIC_PATH=
"""

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
