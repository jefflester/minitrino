# Environment Variables and Config

## Overview

- [Environment Variables and Config](#environment-variables-and-config)
  - [Overview](#overview)
  - [Command Line Options](#command-line-options)
  - [Shell Environment Variables](#shell-environment-variables)
  - [`minitrino.cfg` File](#minitrinocfg-file)
  - [`minitrino.env` File](#minitrinoenv-file)
  - [Text Editor](#text-editor)

Environment variables and configuration are sourced through the following
(**listed in the order of precedence**):

- Command line options (`minitrino -e ...`)
- Shell environment variables
- Variables set in `minitrino.cfg`
- Variables set in the library's `minitrino.env` file

## Command Line Options

Environment variables can be passed to any Minitrino command with the `--env` /
`-e` options:

```sh
minitrino -e CLUSTER_VER=476 provision
minitrino -e IMAGE=starburst -e CLUSTER_VER=476-e provision
minitrino -e LIC_PATH=~/starburstdata.license -e CLUSTER_VER=476-e provision
```

These variables have the highest order of precedence and will override all other
variables.

## Shell Environment Variables

The following shell environment variables are picked up by the CLI:

- `CLUSTER_NAME` - Name of the cluster (defaults to `default`)
- `CLUSTER_VER` - Version of Trino or Starburst to use (e.g., `476` or `476-e`)
- `CONFIG_PROPERTIES` - Additional Trino/Starburst config properties
- `DOCKER_HOST` - Docker daemon socket location
- `IMAGE` - Distribution to use: `trino` or `starburst` (defaults to `trino`)
- `JVM_CONFIG` - Additional JVM configuration
- `LIB_PATH` - Path to Minitrino library files
- `LIC_PATH` - Path to Starburst license file (for Enterprise modules)
- `TEXT_EDITOR` - Text editor to use for config commands

All other shell variables are ignored.

## `minitrino.cfg` File

The following represents the default configuration file:

```cfg
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
```

This file can be directly edited by running:

```sh
minitrino config
```

## `minitrino.env` File

The library's `minitrino.env` file defines image tags and ports used by modules.

### Port Variables

The following port variables control service port mappings (prefixed with
`__PORT_`):

- `__PORT_CACHE_SERVICE` - Cache service port (default: 8180)
- `__PORT_DB2` - DB2 database port (default: 50000)
- `__PORT_ICEBERG_REST_METASTORE` - Iceberg REST metastore port (default: 8181)
- `__PORT_LDAP` - LDAP server port (default: 636)
- `__PORT_MARIA_DB` - MariaDB port (default: 3306)
- `__PORT_MINIO` - MinIO object storage port (default: 9000)
- `__PORT_MINITRINO` - Main Trino/Starburst coordinator port (default: 8080)
- `__PORT_MINITRINO_TLS` - TLS-enabled coordinator port (default: 8443)
- `__PORT_MYSQL` - MySQL database port (default: 3306)
- `__PORT_MYSQL_EVENT_LISTENER_DB` - MySQL event listener database port
  (default: 3306)
- `__PORT_OAUTH2_SERVER` - OAuth2 server port (default: 8100)
- `__PORT_PINOT_CONTROLLER` - Apache Pinot controller port (default: 9090)
- `__PORT_POSTGRES` - PostgreSQL database port (default: 5432)
- `__PORT_SQL_SERVER` - SQL Server port (default: 1433)
- `__PORT_STARBURST_GATEWAY` - Starburst Gateway port (default: 9080)

### Version Variables

The following variables define container image versions used by modules:

- `CLICKHOUSE_VER` - ClickHouse database version (default: 23.10-alpine)
- `CLUSTER_VER` - Trino/Starburst version (default: 476)
- `CURL_VER` - cURL tool version (default: 8.14.1)
- `DB2_VER` - IBM DB2 version (default: 11.5.8.0)
- `ELASTICSEARCH_VER` - Elasticsearch version (default: 8.18.2)
- `HMS_VER` - Hive Metastore version (default: 3.1.3)
- `ICEBERG_REST_VER` - Iceberg REST catalog version (default: 1.6.0)
- `KDC_VER` - Kerberos KDC version (default: alpine_3.19.0)
- `MARIADB_VER` - MariaDB version (default: 10.11)
- `MINIO_MC_VER` - MinIO client version (default: RELEASE.2025-05-21T01-59-54Z)
- `MINIO_VER` - MinIO server version (default: RELEASE.2025-05-24T17-08-30Z)
- `MYSQL_EVENT_LISTENER_VER` - MySQL event listener DB version (default: 8)
- `MYSQL_VER` - MySQL version (default: 8)
- `OAUTH2_SERVER_VER` - OAuth2 mock server version (default: 2.2.1)
- `OPEN_LDAP_VER` - OpenLDAP version (default: 1.5.0)
- `PINOT_VER` - Apache Pinot version (default: 1.2.0)
- `POSTGRES_HMS_VER` - PostgreSQL for Hive Metastore version (default: 13)
- `POSTGRES_SEP_BACKEND_SVC_VER` - PostgreSQL for SEP backend services version
  (default: 13)
- `POSTGRES_VER` - PostgreSQL version (default: 13)
- `SCIM_PYTHON_VER` - Python version for SCIM server (default: 3.10-slim)
- `SQLSERVER_VER` - SQL Server version (default: 2022-latest)
- `STARBURST_GATEWAY_VER` - Starburst Gateway version (default: 6)
- `UBUNTU_VER` - Ubuntu base image version (default: 22.04)
- `ZOOKEEPER_VER` - Apache ZooKeeper version (default: 3.9.2)

### Overriding Variables

To change image tags or ports, the `.env` file can be directly edited, or the
variables can be overridden by either (1) setting them in `minitrino.cfg` or (2)
passing them to the CLI with the `-e` option:

```sh
# Override a specific service version
minitrino -e POSTGRES_VER=15 provision -m postgres

# Override the cluster version
minitrino -e CLUSTER_VER=475 provision

# Override a port to avoid conflicts
minitrino -e __PORT_MINITRINO=8090 provision
```

### Precedence Example

Here's a practical example showing how precedence works:

```sh
# In minitrino.env: CLUSTER_VER=476
# In minitrino.cfg: CLUSTER_VER=475
# Shell environment: export CLUSTER_VER=474
# Command line: minitrino -e CLUSTER_VER=473 provision

# Result: CLUSTER_VER=473 (command line wins)
```

If you remove the command line option:

```sh
# In minitrino.env: CLUSTER_VER=476
# In minitrino.cfg: CLUSTER_VER=475
# Shell environment: export CLUSTER_VER=474
# Command line: minitrino provision

# Result: CLUSTER_VER=474 (shell environment wins)
```

## Text Editor

This is mainly used for `minitrino config`. Common values are `vi`, `nano`, and
`code`.

```text
TEXT_EDITOR=vi
```
