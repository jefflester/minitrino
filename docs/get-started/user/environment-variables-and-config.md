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

The library's `minitrino.env` file defines image tags used by modules. Here is
an example of the file's contents:

```text
CLUSTER_VER=476
ELASTICSEARCH_VER=8.18.2
HMS_VER=3.1.3
MYSQL_VER=8
POSTGRES_VER=13
...
```

Based on the `.env` file above, this Docker Compose snippet would register `13`
for `${POSTGRES_VER}`

```yaml
services:
  postgres:
    image: postgres:${POSTGRES_VER}
```

To change image tags, the `.env` file can be directly edited, or the variables
can be overridden by either (1) setting them in `minitrino.cfg` or (2) passing
them to the CLI with the `-e` option, e.g.:

```sh
minitrino -e POSTGRES_VER=15 provision -m postgres
minitrino -e CLUSTER_VER=475 provision
```

## Text Editor

This is mainly used for `minitrino config`. Common values are `vi`, `nano`, and
`code`.

```text
TEXT_EDITOR=vi
```
