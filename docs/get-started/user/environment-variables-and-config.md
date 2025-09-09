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
minitrino -e STARBURST_VER=427-e provision
minitrino -e LIC_PATH=~/starburstdata.license -e STARBURST_VER=429-e provision
```

These variables have the highest order of precedence and will override all other
variables.

## Shell Environment Variables

The following shell environment variables are picked up by the CLI:

- `CONFIG_PROPERTIES`
- `DOCKER_HOST`
- `JVM_CONFIG`
- `LIB_PATH`
- `STARBURST_VER`
- `TEXT_EDITOR`
- `LIC_PATH`

All other shell variables are ignored.

## `minitrino.cfg` File

The following represents the default configuration file:

```cfg
[config]
# defaults to ~/.minitrino/lib
LIB_PATH=

STARBURST_VER=
TEXT_EDITOR=
LIC_PATH=
```

This file can be directly edited by running:

```sh
minitrino config
```

## `minitrino.env` File

The library's `minitrino.env` file defines image tags used by modules. Here is
an example of the file's contents:

```text
COMPOSE_PROJECT_NAME=minitrino

ELASTICSEARCH_VER=8.11.0
HMS_VER=3.1.3
MYSQL_VER=8
POSTGRES_VER=11
STARBURST_VER=423-e.6
...
```

Based on the `.env` file above, this Docker Compose snippet would register `11`
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
```

## Text Editor

This is mainly used for `minitrino config`. Common values are `vi`, `nano`, and
`code`.

```text
TEXT_EDITOR=vi
```
