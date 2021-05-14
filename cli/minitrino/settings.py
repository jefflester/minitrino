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
MODULE_CATALOG = "catalog"
MODULE_SECURITY = "security"
MODULE_RESOURCES = "resources"
ETC_TRINO = "/etc/starburst"
TRINO_CONFIG = "config.properties"
TRINO_JVM_CONFIG = "jvm.config"
LIB_INDEPENDENT_CMDS = ["lib_install"]

# Snapshots
SNAPSHOT_ROOT_FILES = ["docker-compose.yml", "minitrino.env", "Dockerfile", "version"]

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
[CLI]
LIB_PATH=
TEXT_EDITOR=

[DOCKER]
DOCKER_HOST=

[TRINO]
CONFIG=
JVM_CONFIG=

[MODULES]
STARBURST_LIC_PATH=

S3_ENDPOINT=s3.region.amazonaws.com
S3_ACCESS_KEY=
S3_SECRET_KEY=
AWS_REGION=

SNOWFLAKE_DIST_CONNECT_URL=
SNOWFLAKE_DIST_CONNECT_USER=
SNOWFLAKE_DIST_CONNECT_PASSWORD=
SNOWFLAKE_DIST_WAREHOUSE=
SNOWFLAKE_DIST_DB=
SNOWFLAKE_DIST_STAGE_SCHEMA=

SNOWFLAKE_JDBC_CONNECT_URL=
SNOWFLAKE_JDBC_CONNECT_USER=
SNOWFLAKE_JDBC_CONNECT_PASSWORD=
SNOWFLAKE_JDBC_WAREHOUSE=
SNOWFLAKE_JDBC_DB=
SNOWFLAKE_JDBC_STAGE_SCHEMA=
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
