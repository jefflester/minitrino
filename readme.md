# Minitrino

A command line tool that makes it easy to run modular Trino environments
locally. Compatible with Starburst versions 388-e and later.

[![PyPI
version](https://badge.fury.io/py/minitrino.svg)](https://badge.fury.io/py/minitrino)
![Build
Status](https://github.com/jefflester/minitrino/actions/workflows/tests.yml/badge.svg)
[![Trino
Slack](https://img.shields.io/static/v1?logo=slack&logoColor=959DA5&label=Slack&labelColor=333a41&message=join%20conversation&color=3AC358)](https://trinodb.io/slack.html)

-----

**Latest Stable Release**: 2.0.4

-----

## Overview

- [Minitrino](#minitrino)
  - [Overview](#overview)
  - [Requirements](#requirements)
  - [Installation and Upgrades](#installation-and-upgrades)
    - [End Users](#end-users)
    - [Developers](#developers)
    - [Using Colima and Other Docker Contexts](#using-colima-and-other-docker-contexts)
    - [End User Upgrades](#end-user-upgrades)
  - [Workflow Examples](#workflow-examples)
    - [Provision an Environment](#provision-an-environment)
    - [Modify Files in a Running Container](#modify-files-in-a-running-container)
    - [Shut Down an Environment](#shut-down-an-environment)
    - [Remove Minitrino Resources](#remove-minitrino-resources)
    - [Snapshot a Customized Module](#snapshot-a-customized-module)
  - [Minitrino Configuration File](#minitrino-configuration-file)
    - [\[CLI\] Section](#cli-section)
    - [\[MODULES\] Section](#modules-section)
  - [Project Structure](#project-structure)
    - [Trino Dockerfile](#trino-dockerfile)
  - [Add New Modules (Tutorial)](#add-new-modules-tutorial)
    - [Create the Module Directory](#create-the-module-directory)
    - [Add Trino Resources](#add-trino-resources)
    - [Add the Docker Compose YAML](#add-the-docker-compose-yaml)
    - [Add a Metadata File](#add-a-metadata-file)
    - [Add a Readme File](#add-a-readme-file)
    - [Review Progress](#review-progress)
    - [Configure the Docker Compose YAML File](#configure-the-docker-compose-yaml-file)
    - [Important Implementation Details: Paths and Labels](#important-implementation-details-paths-and-labels)
      - [Path References for Volumes and Build Contexts](#path-references-for-volumes-and-build-contexts)
      - [Minitrino Docker Labels](#minitrino-docker-labels)
    - [Test the New Catalog](#test-the-new-catalog)
    - [Bootstrap Scripts](#bootstrap-scripts)
      - [Installing Shell Packages for Bootstrap Scripts](#installing-shell-packages-for-bootstrap-scripts)
    - [Managing Trino's `config.properties` and `jvm.config` Files](#managing-trinos-configproperties-and-jvmconfig-files)
      - [Preferable Method: Environment Variables](#preferable-method-environment-variables)
      - [Secondary Method: Bootstrap Scripts](#secondary-method-bootstrap-scripts)
  - [Troubleshooting](#troubleshooting)
  - [Reporting Bugs and Contributing](#reporting-bugs-and-contributing)

-----

## Requirements

- Docker Desktop >= 3.5
- Python >= 3.8
- Pip
- Linux / MacOS

-----

## Installation and Upgrades

### End Users

Minitrino is available on PyPI and the library is available for public download
on GitHub. To set everything up, run:

```sh
  pip install minitrino
  minitrino -v lib-install
```

Using this installation method, the `LIB_PATH` variable will point to
`~/.minitrino/lib/`.

### Developers

In the project's root directory, run `./install.sh` to install the Minitrino
CLI. If you encounter errors during installation, try running `sudo -H
./install.sh -v`.

Using this installation method, the `LIB_PATH` variable will point to
`${MINITRINO_REPOSITORY_DIRECTORY}/lib/`.

### Using Colima and Other Docker Contexts

For users not operating on the default Docker Desktop context, you can set the
`DOCKER_HOST` shell environment variable to point to the desired context's
`.sock` file, e.g.:

```sh
echo 'export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"' >> ~/.bash_profile
```

### End User Upgrades

To upgrade the Minitrino CLI, run:

```sh
pip install minitrino --upgrade
```

Each CLI version has its own respective library. To install the updated library,
run:

```sh
minitrino -v lib-install
```

**Note**: Installing the new library will overwrite all modules and snapshots in
the current library. If you have customized modules or snapshot files in
`lib/snapshots/`, make sure to take a backup of the `~/.minitrino/lib` directory
prior to running this command in order to persist your local changes.

-----

## Workflow Examples

Minitrino is best suited for local Trino development. This project is not
intended for usage on a large scale, and is intentionally designed to limit the
deployment to a single coordinator container.

### Provision an Environment

Provision the `postgres` module with a specific SEP version:

```sh
minitrino -v -e STARBURST_VER=${VER} provision -m postgres
```

Provision the `iceberg` and `oauth2` modules:

```sh
minitrino -v provision -m postgres -m oauth2
```

Append the running environment with a third module:

```sh
minitrino -v provision -m postgres -m oauth2 -m hive
```

All environments expose the Starburst service on `localhost:8080`, meaning you
can visit the web UI directly, or you can connect external clients, such as
DBeaver, to the `localhost` service. The `trino` container shell can be directly
accessed via:

```sh
docker exec -it trino bash 
```

### Modify Files in a Running Container

You can modify files inside a running container with this workflow:

```sh
docker exec -it trino bash 
echo "io.trino=DEBUG" >> /etc/starburst/log.properties
exit
docker restart trino
```

### Shut Down an Environment

```sh
minitrino down
```

### Remove Minitrino Resources

To remove all images, run:

```sh
minitrino remove --images
```

To remove images from a specific module, run:

```sh
minitrino remove --images \
  --label com.starburst.tests.module.${MODULE}=${MODULE_TYPE}-${MODULE}
```

Where `${MODULE_TYPE}` is one of: `admin`, `catalog`, `security`.

You can also use the `remove` command to remove individual volumes with the
`--volumes` option.

### Snapshot a Customized Module

Users designing and customizing their own modules can persist them with the
`snapshot` command. For example, if a user has modified the `hive` module, they
can persist their changes by running:

```sh
minitrino snapshot --name ${SNAPSHOT_NAME} -m hive
```

By default, the snapshot file is placed in
`${LIB_PATH}/${SNAPSHOT_NAME}.tar.gz`. The snapshot can be saved to a different
directory by passing the `--directory` option to the `snapshot` command.

-----

## Minitrino Configuration File

Sticky configuration is set in `~/.minitrino/minitrino.cfg`. The sections in
this file each serve a separate purpose.

### [CLI] Section

These configs allow the user to customize the behavior of Minitrino.

- `LIB_PATH`: The filesystem path of the Minitrino library (specifically to the
  `lib/` directory).
- `TEXT_EDITOR`: The text editor to use with the `config` command, e.g. "vi",
  "nano", etc. Defaults to the shell's default editor.

### [MODULES] Section

This section has only one default config: `SEP_LIC_PATH`. This is required if
using licensed Starburst Enterprise features. It can point to any valid license
on your filesystem.

This section can also be used to set environment variables passed to containers
provisioned by Minitrino. Environment variables are only passed to a container
if the variable is specified in the module's `docker-compose.yml` file.

For example, if your `minitrino.cfg` config file contains this variable:

```bash
DB_PASSWORD=password123
```

And your `docker-compose.yml` file contains this:

```yaml
services:
  trino:
    environment:
      DB_PASSWORD: ${DB_PASSWORD}
```

Then `DB_PASSWORD` is accessible inside of the Trino container as an environment
variable. This functionality can be applied to any container as long as the
convention above is followed.

-----

## Project Structure

The library is built around Docker Compose files and utilizes Docker's ability
to [extend Compose
files](https://docs.docker.com/compose/extends/#multiple-compose-files).

The Starburst Trino service is defined in a Compose file at the library root,
and all other services look up in the directory tree to reference the parent
Trino service.

A simplified library structure:

```sh
lib
├── Dockerfile
├── docker-compose.yml
├── minitrino.env
├── modules
│   ├── admin
│   │   └── ...
│   ├── catalog
│   │   └── postgres
│   │       ├── metadata.json
│   │       ├── postgres.yml
│   │       ├── readme.md
│   │       └── resources
│   │           ├── postgres
│   │           │   └── postgres.env
│   │           └── trino
│   │               └── postgres.properties
│   ├── resources
│   └── security
│       └── ...
├── snapshots
└── version
```

### Trino Dockerfile

Minitrino modifies Starburst's Docker image by adding the Trino CLI to the image
as well as by adding `sudo` privileges to the `trino` user. This is required for
certain bootstrap scripts (i.e. using `microdnf` to install packages in a Trino
container for a module).

-----

## Add New Modules (Tutorial)

Adding new modules is relatively simple, but there are a few important
guidelines to follow to ensure compatibility with the Minitrino CLI. Module
design principals are the same all modules. The example below demonstrates the
process of creating a new catalog module for a Postgres service.

### Create the Module Directory

Create the module's directory in the `lib/modules/catalog/` directory:

```sh
mkdir lib/modules/catalog/my-postgres/
cd lib/modules/catalog/my-postgres/
```

### Add Trino Resources

All resources for a module go inside of a `resources/` directory within the
module. Inside this directory, place Trino-specific resources into a `trino/`
directory, then mount the resources to the Trino service defined in the root
`docker-compose.yml` file.

```sh
mkdir -p resources/trino/
```

In the newly-created `resources/trino/` directory, add a properties file.

```sh
bash -c "cat << EOF > postgres.properties
connector.name=postgresql
connection-url=jdbc:postgresql://postgres:5432/minitrino
connection-user=admin
connection-password=trinoRocks15
EOF"
```

-----

**Note**: Passwords in the default modules tend to be `trinoRocks15`. For
consistency throughout the library, it is recommended to use this as the
password of choice for new module development.

-----

### Add the Docker Compose YAML

In `lib/modules/catalog/my-postgres/`, add a Docker Compose file:

```sh
touch my-postgres.yml
```

Notice the naming convention: `my-postgres.yml`. Giving the same root name of
"my-postgres" to both the parent directory `my-postgres/` and to the Docker
Compose file `my-postgres.yml` will allow Minitrino to find the new catalog
module.

Next, add an environment file for the Postgres service. Non-Trino resources
should go into their own directory, so create one for postgres:

```sh
mkdir resources/postgres/
```

In the newly-created directory, add an environment file which will register the
variables in the Postgres container when it is provisioned:

```sh
bash -c "cat << EOF > postgres.env
POSTGRES_USER=admin
POSTGRES_PASSWORD=trinoRocks15
POSTGRES_DB=minitrino
EOF"
```

This file will initialize Postgres with a database `minitrino`, a user `trino`,
and a password `trinoRocks15`.

### Add a Metadata File

The `metadata.json` file allows Minitrino to obtain key information about the
module. **It is required for a module to work with the CLI.**

In `lib/modules/catalog/my-postgres/`, add a `metadata.json` file:

```sh
bash -c 'cat << EOF > metadata.json
{
  "description": "Creates a Postgres catalog using the standard Postgres connector.",
  "incompatibleModules": [],
  "dependentModules": [],
  "enterprise": false
}
EOF'
```

- `description`: describes the module.
- `incompatibleModules`: restricts certain modules from being provisioned
alongside the given module. The `*` wildcard is a supported convention if the
module is incompatible with all other modules.
- `dependentModules`: specifies which modules must be provisioned alongside the
target. Dependent modules will be automatically provisioned with the `provision`
command.
- `enterprise`: requires a Starburst license file (`starburstdata.license`).

The metadata file information can be exposed via the `modules` command.

### Add a Readme File

This step is not required for personal development, but it is required to commit
a module to the Minitrino repository.

In `lib/modules/catalog/my-postgres/`, add a `readme.md` file:

```sh
touch readme.md
```

This file should contain an overview of the module.

### Review Progress

The resulting directory tree should look like this (from the
`lib/modules/catalog/` directory):

```sh
my-postgres
├── metadata.json
├── my-postgres.yml
├── readme.md
└── resources
    ├── postgres
    │   └── postgres.env
    └── trino
        └── postgres.properties
```

### Configure the Docker Compose YAML File

We will now define the `my-postgres.yml` Docker Compose file. Set it up as
follows:

```yaml
version: '3.8'
services:

  trino:
    volumes:
      - ./modules/catalog/my-postgres/resources/trino/postgres.properties:/etc/starburst/catalog/postgres.properties

  postgres:
    image: postgres:${POSTGRES_VER}
    container_name: postgres
    env_file:
      - ./modules/catalog/my-postgres/resources/postgres/postgres.env
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.my-postgres=catalog-my-postgres

```

### Important Implementation Details: Paths and Labels

We can observe a few things about the Compose file we just defined.

#### Path References for Volumes and Build Contexts

First, the volumes we mount *are not relative to the Compose file itself*, they
are relative to the base `docker-compose.yml` file in the library root. This is
because the CLI extends Compose files, meaning that all path references in child
Compose files need to be relative to the positioning of the parent Compose file.

The base Compose file is determined when you execute a Docker Compose
command––the first Compose file referenced in the command becomes the base file,
and that happens to be the `docker-compose.yml` file in the library root. This
is how Minitrino constructs these commands.

If this is confusing, you can read more about extending Compose files on the
[Docker docs](https://docs.docker.com/compose/extends/#multiple-compose-files).

#### Minitrino Docker Labels

Secondly, notice the applied sets of labels to the Postgres service. These
labels tell the CLI which resources to target when executing commands.

In general, there is no need to apply labels to the Trino service since they are
already applied in the parent Compose file **unless** the module is an extension
of the Trino service itself (i.e. the `biac` module). Labels should always be
applied to:

- Docker services (AKA the resulting container)
- Persistent volumes
- Images built from a Dockerfile (see the main `docker-compose.yml` file for an
  example)

Labels should be defined in pairs of two. The convention is:

- The standard Minitrino resource label: `com.starburst.tests=minitrino`
- A module-specific resource label:
  `com.starburst.tests.module.${MODULE_NAME}=${MODULE_CATEGORY}-${MODULE_NAME}`
  - For this label, the `module-type` should be one of: `admin`, `catalog`, or
    `security`
  - This applies a unique label to the module, allowing it to be isolated when
    necessary

In Compose files where multiple services are defined, all services should be
labeled with the same label sets (see the `hive` for an example).

-----

**Note**: A named volume is defined explicitly in the Compose file, and these
should always have label sets applied to them. Below is an example of the
Compose file we just created with a named volume.

-----

```yaml
version: '3.8'
services:

  trino:
    volumes:
      - ./modules/catalog/my-postgres/resources/trino/postgres.properties:/etc/starburst/catalog/postgres.properties

  postgres:
    image: postgres:${POSTGRES_VER}
    container_name: postgres
    env_file:
      - ./modules/catalog/my-postgres/resources/postgres/postgres.env
    labels: # These labels are applied to the service/container
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.my-postgres=catalog-my-postgres

volumes:
  postgres-data:
    labels: # These labels are applied to the named volume
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.my-postgres=catalog-my-postgres
```

-----

**Note**: Certain modules will only extend the parent Trino service and do not
actually define any new services/containers. See the `biac` module for an
example of this. For these modules, the only label requirement is to add the
module-specific label to the Trino service in the relevant `docker-compose.yml`
file.

-----

### Test the New Catalog

We are all finished up. We can test our new catalog through the Minitrino CLI:

```sh
minitrino provision -m my-postgres
```

We can now open a shell session in the `trino` container and run some tests:

```sh
docker exec -it trino bash 
trino-cli
trino> show catalogs;
```

### Bootstrap Scripts

Minitrino supports container bootstrap scripts. These scripts **do not replace**
the entrypoint (or default command) for a given container. The script is copied
from the Minitrino library to the container, executed, and then removed from the
container. Containers are restarted after each bootstrap script execution, **so
the bootstrap scripts themselves should not restart the container's service**.

If a bootstrap script has already executed in a container *and* the volume
associated with the container still exists, Minitrino will not re-execute the
bootstrap script *unless the contents of the script have changed*. The is useful
after running `minitrino down --keep` (which does not remove unnamed container
volumes), so that the subsequent `provision` command will not re-execute the
same bootstrap script(s).

If a bootstrap script is updated, it is recommended to destroy the associated
container(s) via `minitrino down` and then to re-provision.

To add a bootstrap script, add a `resources/bootstrap/` directory in any given
module, create a shell script, and then reference the script name in the Compose
YAML file:

```yaml
version: '3.8'
services:

  trino:
    environment:
      MINITRINO_BOOTSTRAP: bootstrap.sh
```

The `elasticsearch` module is a good example of this.

#### Installing Shell Packages for Bootstrap Scripts

If you need to install a shell package for a bootstrap script, it is recommended
that the package be added at the Dockerfile level instead of within the
bootstrap script. This is to ensure compatibility between SEP Trino-based
releases.

To add the necessary package, simply update shell dependencies in
`lib/dockerfile-resources/configure.sh`.

### Managing Trino's `config.properties` and `jvm.config` Files

Many modules may change the Trino `config.properties` and `jvm.config` files.
There are two supported ways to modify these files with within the `trino`
container.

#### Preferable Method: Environment Variables

Minitrino has special support for two Trino-specific environment variables:
`CONFIG_PROPERTIES` and `JVM_CONFIG`. Below is an example of setting these
variables:

```yaml
trino:
  environment:
    CONFIG_PROPERTIES: |-
      insights.jdbc.url=jdbc:postgresql://postgresdb:5432/insights
      insights.jdbc.user=admin
      insights.jdbc.password=password
      insights.persistence-enabled=true
    JVM_CONFIG: |-
      -Xlog:gc:/var/log/sep-gc-%t.log:time:filecount=10
```

#### Secondary Method: Bootstrap Scripts

The `config.properties` and `jvm.config` files can also be modified directly
with a Trino [bootstrap script](#bootstrap-scripts).

-----

## Troubleshooting

- If you experience issues executing a Minitrino command, re-run it with the
  `-v` option for verbose output. This will often reveal the issue's root cause.
- If you experience an issue with a particular Docker container, consider
  running these commands:
  - `docker logs ${CONTAINER_NAME}`: Print the logs for a given container to the
    terminal
  - `docker ps`: Show all running Docker containers and associated statistics
  - `docker inspect ${CONTAINER_NAME}` to see various details about a container
- If you experience issues with a library module, check that that module is
  structured correctly according to the [module
  tutorial](#add-new-modules-tutorial), and ensure the library and the CLI
  versions match
- Sometimes, a lingering persistent volume can cause problems (i.e. a stale Hive
  metastore database volume from a previous module deployment), so you can run:
  - `minitrino down`
  - `minitrino -v remove --volumes` to remove **all** existing Minitrino
    volumes. Alternatively, run `minitrino -v remove --volumes --label <your
    label>` to specify a specific module for which to remove volumes. See the
    [removing resources](#remove-minitrino-resources) section for more
    information.

If none of these troubleshooting tips help to resolve your issue, [please file a
GitHub issue](#reporting-bugs-and-contributing) and provide as much information
as possible.

-----

## Reporting Bugs and Contributing

To report bugs, please file a GitHub issue on the [Minitrino
repository](https://github.com/jefflester/minitrino). Bug reports should:

- Contain any relevant log messages (if the bug is tied to a command, running
  with the `-v` flag will make debugging easier)
- Describe what the expected outcome is
- Describe the proposed code fix (optional)

Contributors have two options:

1. Fork the repository, then make a PR to merge your changes
2. If you have been added as a contributor, you can go with the method above or
   you can create a feature branch, then submit a PR for that feature branch
   when it is ready to be merged.

In either case, please provide a comprehensive description of your changes with
the PR.
