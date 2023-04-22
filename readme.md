# Minitrino

A command line tool that makes it easy to run modular Trino environments
locally. Compatible with Starburst versions 370-e and later.

[![PyPI
version](https://badge.fury.io/py/minitrino.svg)](https://badge.fury.io/py/minitrino)
[![Build
Status](https://travis-ci.org/jefflester/minitrino.svg?branch=master)](https://app.travis-ci.com/jefflester/minitrino.svg?branch=master)
[![Trino
Slack](https://img.shields.io/static/v1?logo=slack&logoColor=959DA5&label=Slack&labelColor=333a41&message=join%20conversation&color=3AC358)](https://trinodb.io/slack.html)

-----

**Latest Stable Release**: 2.0.2

-----

## Overview

- [Minitrino](#minitrino)
  - [Overview](#overview)
  - [Requirements](#requirements)
  - [Installation](#installation)
    - [End Users](#end-users)
    - [Developers](#developers)
  - [CLI](#cli)
    - [Top-Level CLI Options](#top-level-cli-options)
    - [Provisioning Environments](#provisioning-environments)
      - [Environment Variables](#environment-variables)
      - [Using Licensed Starburst Features](#using-licensed-starburst-features)
    - [Removing Resources](#removing-resources)
    - [Shutting Down Environments](#shutting-down-environments)
    - [Taking Environment Snapshots](#taking-environment-snapshots)
    - [Manage User Configuration](#manage-user-configuration)
    - [Install the Library](#install-the-library)
    - [Display Module Metadata](#display-module-metadata)
    - [Display Minitrino Versions](#display-minitrino-versions)
    - [Pointing the CLI to the Minitrino Library](#pointing-the-cli-to-the-minitrino-library)
  - [Minitrino Configuration File](#minitrino-configuration-file)
    - [\[CLI\] Section](#cli-section)
    - [\[MODULES\] Section](#modules-section)
  - [Project Structure](#project-structure)
    - [Trino Dockerfile](#trino-dockerfile)
  - [Adding New Modules (Tutorial)](#adding-new-modules-tutorial)
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
    - [Customizing Images](#customizing-images)
    - [Bootstrap Scripts](#bootstrap-scripts)
      - [Installing Shell Packages for Bootstrap Scripts](#installing-shell-packages-for-bootstrap-scripts)
    - [Managing Trino's `config.properties` and `jvm.config` Files](#managing-trinos-configproperties-and-jvmconfig-files)
  - [Troubleshooting](#troubleshooting)
  - [Reporting Bugs and Contributing](#reporting-bugs-and-contributing)

-----

## Requirements

- Docker 19.03.0+
- Docker Compose (1.29.0+)
- Python 3.8+
- Pip
- Linux or Mac OS

-----

## Installation

### End Users

Minitrino is available on PyPI and the library is available for public download
on GitHub. To install the Minitrino CLI, run `pip install minitrino`. To install
the library, run `minitrino lib_install`.

### Developers

In the project's root, run `./install.sh` to install the Minitrino CLI. If you
encounter errors during installation, try running `sudo -H ./install.sh -v`.

-----

## CLI

Minitrino is built with [Click](https://click.palletsprojects.com/en/7.x/), a
popular, open-source toolkit used to build Python-based CLIs.

All Minitrino commands/options are documented below. Note that many command
options can be specified with a shorthand alternative, which is the first letter
of each option, i.e. `--module` can be `-m`.

### Top-Level CLI Options

You can get help, enable verbose output, and change the runtime library
directory for any command.

```
Usage: minitrino [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose   Enable verbose output.
  -e, --env TEXT  Add or override environment variables.
                  
                  Environment variables are sourced from the Minitrino
                  library's root 'minitrino.env' file as well as the user 
                  config file in '~/.minitrino/minitrino.cfg'. Variables 
                  supplied by this option will override values from either 
                  of those sources. The variables will also be passed to the
                  environment of the shell executing commands during the
                  'provision' command.

  --help          Show this message and exit.
```

### Provisioning Environments

You can provision an environment via the `provision` command.

```
Usage: minitrino provision [OPTIONS]

  Provision an environment based on specified modules. All options are
  optional and can be left empty.

Options:
  -m, --module TEXT         A specific module to provision.
  -n, --no-rollback         Do not rollback provisioned resources in the event
                            of an error.

  -d, --docker-native TEXT  Appends native docker-compose commands to the
                            generated docker-compose shell command. Run
                            `docker-compose up --help` to see all available
                            options.
                            
                            Example: minitrino provision --docker-native
                            --build
                            
                            Example: minitrino provision --docker-native '--
                            remove-orphans --force-recreate'

  --help                    Show this message and exit.
```

Notes:

- If no options are passed in, the CLI will provision a standalone Trino
  container.
- The command cannot currently be used to append additional modules to an active
  environment. To modify an environment, first shut it down, then re-provision
  with the needed modules.

Sample `provision` commands:

```bash
minitrino provision \
  --module hive-s3 \
  --module elasticsearch \
  --module ldap \
  --docker-native '--build --force-recreate'

minitrino provision -m hive-s3 -m elasticsearch -m ldap

minitrino --env STARBURST_VER=332-e.6 provision
```

The `provision` command constructs a Docker Compose command and executes it in
the host shell. The commands look similar to:

```bash
ENV_VAR_1=SOMETHING ENV_VAR_2=SOMETHING ENV_VAR_3=${ENV_VAR_3} ... \
docker-compose -f docker-compose.yml \
  -f modules/catalog/elasticsearch/elasticsearch.yml \
  -f modules/catalog/hive-s3/hive-s3.yml \
  -f modules/security/ldap/ldap.yml \
  up -d
```

Using the structure of the Minitrino library, it is able to merge multiple
Docker Compose files together.

#### Environment Variables

Environment variables passed to Docker containers are sourced through two
locations. The first is from the `minitrino.env` file in the library root. These
variables define the versions of the provisioned Docker services. The second is
from from variables set in the `[MODULES]` section of the `minitrino.cfg` file.
These variables can contain sensitive information like access credentials, so
their values are intentionally left out of library files.

Any existing environment variable can be overridden with the top-level `--env`
option, and any unset variable can be set with it.

#### Using Licensed Starburst Features

If you are using licensed features, you will need to provide a path to a valid
Starburst license. This can be set via `minitrino config` or provided via the
`--env` option at command runtime. The variable for this is
`STARBURST_LIC_PATH`.

Additionally, you need to uncomment the volume mount in the library's root
`docker-compose.yml` file:

```yaml
  # Uncomment this to enable the volume mount. The variable should point to a
  # valid SEP license. 
  volumes:
    - "${STARBURST_LIC_PATH}:/etc/starburst/starburstdata.license:ro"
```

### Removing Resources

You can remove resources with the `remove` command.

```
Usage: minitrino remove [OPTIONS]

  Remove Minitrino resources.

Options:
  -i, --images      Remove Minitrino images.
  -v, --volumes     Remove Minitrino container volumes.
  -l, --label TEXT  Target specific labels for removal (format: key-value
                    pair(s)).

  -f, --force       Force the removal of Minitrino resources. Normal Docker
                    removal restrictions apply.

  --help            Show this message and exit.
```

Notes:

- Named volumes tied to any *existing* container cannot be forcibly removed,
  neither by Minitrino nor by the Docker CLI/SDK.
- Images tied to stopped containers can be forcibly removed, but any image tied
  to a running container cannot be forcibly removed, neither by Minitrino nor by
  the Docker CLI.
- You can find a module's label key by looking at the module's
  `docker-compose.yml` file in the Minitrino library.

Sample `remove` command:

```bash
minitrino -v remove \
  --volumes \
  --label com.starburst.tests.module.postgres=catalog-postgres \
  --force
```

This will only remove volumes associated to the Postgres catalog module.

### Shutting Down Environments

You can shut down an active environment with the `down` command.

```
Usage: minitrino down [OPTIONS]

  Bring down running Minitrino containers. This command follows the
  behavior of `docker-compose down` where containers are both stopped and
  removed.

Options:
  -k, --keep  Does not remove containers; instead, containers will only be
              stopped.

  --sig-kill  Stop Minitrino containers without a grace period.
  --help      Show this message and exit.
```

Sample `down` command:

```bash
minitrino -v down
```

### Taking Environment Snapshots

You can capture snapshots for both active and inactive environments with the
`snapshot` command.

```
Usage: minitrino snapshot [OPTIONS]

  Create a snapshot of a Minitrino environment. A tarball is placed in the
  Minitrino `lib/snapshots/` directory.

  To take a snapshot of an active environment, leave the `--module` and
  option out of the command.

  To take a snapshot of modules whether they are active or not, specify the
  modules via the `--module` option.

Options:
  -m, --module TEXT     A specific module to snapshot.
  -n, --name TEXT       Basename of the resulting snapshot tarball file.
                        Allowed characters: alphanumerics, hyphens, and
                        underscores.  [required]

  -d, --directory PATH  Directory to save the resulting snapshot file in.
                        Defaults to the snapshots directory in the Minitrino
                        library.

  -f, --force           Overwrite the file if it already exists.
  --no-scrub            Do not scrub sensitive data from user config file.
                        
                        WARNING: all sensitive information (passwords and
                        keys) will be kept in the user config file added to
                        the snapshot. Only use this if you are prepared to
                        share those secrets with another person.

  --help                Show this message and exit.
```

Notes:

- Minitrino records the original `provision` command and places it in the
  snapshot file as `provision-snapshot.sh`; this can be directly executed. This
  makes it easier for others to reuse the environment and provision it
  identically.

Sample `snapshot` commands:

```bash
# Take a snapshot of an active environment (this will create a tarball 
# called `snapshot-t2533.tar.gz` in the library's `snapshots/` directory):
minitrino snapshot --name t-2533

# Take a snapshot of specific modules:
minitrino snapshot -n super-cool-env -m hive-s3 -m elasticsearch -m ldap
```

### Manage User Configuration

You can manage Minitrino configuration with the `config` command.

```
Usage: minitrino config [OPTIONS]

  Edit the Minitrino user configuration file.

Options:
  -r, --reset  Reset the Minitrino user configuration file and create a new
               config file from a template.
               
               WARNING: This will remove your configuration file (if it
               exists) and replace it with a template.

  --help       Show this message and exit.
```

### Install the Library

You can install the Minitrino library with the `lib_install` command. Note that
it is best practice to have the library version match the CLI version. You can
check these versions with `minitrino version`.

```
Usage: minitrino lib_install [OPTIONS]

  Install the Minitrino library.

Options:
  -v, --version TEXT  The version of the library to install.
  --help              Show this message and exit.
```

### Display Module Metadata

You can see Minitrino module metadata with the `modules` command.

```
Usage: minitrino modules [OPTIONS]

  Display module metadata.

Options:
  -m, --module TEXT  A specific module to display metadata for.
  -j, --json         Print the resulting metadata in JSON form (shows
                     additional module metadata).

  -r, --running      Print metadata for all running modules.
  --help             Show this message and exit.
```

### Display Minitrino Versions

You can display the Minitrino CLI and library versions with the `version`
command.

```
Usage: minitrino version [OPTIONS]

  Display Minitrino CLI and library versions.

Options:
  --help  Show this message and exit.
```

### Pointing the CLI to the Minitrino Library

The Minitrino CLI should always point to a compatible library with the expected
structure. The library directory can be set one of four ways, listed below in
the order of precedence:

1. Passing the `LIB_PATH` variable to the CLI's `--env` option sets the library
   directory for the current command.
2. The `minitrino.cfg` file's `LIB_PATH` variable sets the library directory if
   present.
3. The path `~/.minitrino/lib/` is used as the default lib path if the
   `LIB_PATH` var is not found.
4. As a last resort, Minitrino will check to see if the library exists in
   relation to the positioning of the `components.py` file and assumes the
   project is being run out of a cloned repository.

If you not running out of a cloned repository, it is advisable to provide a
pointer to the library in Minitrino's configuration via the `LIB_PATH` config.

-----

## Minitrino Configuration File

Sticky configuration is set in `~/.minitrino/minitrino.cfg`. The sections in
this file each serve a separate purpose.

### [CLI] Section

These configs allow the user to customize the behavior of Minitrino.

- LIB_PATH: The filesystem path of the Minitrino library (specifically to the
  `lib/` directory).
- TEXT_EDITOR: The text editor to use with the `config` command, e.g. "vi",
  "nano", etc. Defaults to the shell's default editor.

### [MODULES] Section

This section sets environment variables passed to containers provisioned by
Minitrino. Environment variables are only passed to a container if the variable
is specified in the module's `docker-compose.yml` file.

Variables propagated to the Trino container are supported by Trino secrets.

- STARBURST_LIC_PATH: Required if using licensed Starburst Enterprise Trino
  features. It can point to any valid license on your filesystem.
- S3_ENDPOINT
- S3_ACCESS_KEY
- S3_SECRET_KEY
- AWS_REGION
- SNOWFLAKE_DIST_CONNECT_URL
- SNOWFLAKE_DIST_CONNECT_USER
- SNOWFLAKE_DIST_CONNECT_PASSWORD
- SNOWFLAKE_DIST_WAREHOUSE
- SNOWFLAKE_DIST_DB
- SNOWFLAKE_DIST_STAGE_SCHEMA
- SNOWFLAKE_JDBC_CONNECT_URL
- SNOWFLAKE_JDBC_CONNECT_USER
- SNOWFLAKE_JDBC_CONNECT_PASSWORD
- SNOWFLAKE_JDBC_WAREHOUSE
- SNOWFLAKE_JDBC_DB
- SNOWFLAKE_JDBC_STAGE_SCHEMA

-----

## Project Structure

The library is built around Docker Compose files and utilizes Docker's ability
to [extend Compose
files](https://docs.docker.com/compose/extends/#multiple-compose-files).

The Starburst Trino service is defined in a Compose file at the library root,
and all other services look up in the directory tree to reference the parent
Trino service. In Compose files, the fully-qualified path––relative to the
library's root `docker-compose.yml` file––must be provided for Docker to locate
resources.

A simplified library structure:

```
lib
├── Dockerfile
├── docker-compose.yml
├── minitrino.env
├── modules
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
│   │   └── wait-for-it.sh
│   └── security
│       └── event-logger
│           ├── event-logger.yml
│           ├── metadata.json
│           ├── readme.md
│           └── resources
│               ├── event-logger
│               │   └── postgres.env
│               └── trino
│                   ├── event-listener.properties
│                   └── postgres_event_logger.properties
├── snapshots
└── version
```

And the contents of a `docker-compose.yml` file (`postgres.yml`):

```yaml
version: "3.8"
services:

  trino:
    volumes:
      - "./modules/catalog/postgres/resources/trino/postgres.properties:/etc/starburst/catalog/postgres.properties"

  postgres:
    image: "postgres:${POSTGRES_VER}"
    container_name: "postgres"
    labels:
      - "com.starburst.tests=minitrino"
      - "com.starburst.tests.module.postgres=catalog-postgres"
    env_file:
      - "./modules/catalog/postgres/resources/postgres/postgres.env"
```

Notice that the volume mount is not relative to the
`lib/modules/catalog/postgres/` directory––it is relative to the parent
directory which houses the top-level `docker-compose.yml` file. Also, notice the
labels––these labels will be used to identify Docker resources tied to Minitrino
modules so that the CLI commands actually work.

### Trino Dockerfile

Minitrino modifies the Starburst Trino Docker image by adding the Trino CLI to
the image as well as by providing `sudo` to the `trino` user. This is required
for certain bootstrap scripts (i.e. using `yum` to install packages in a Trino
container for a module). This image is compatible with Starburst Trino images
back to Starburst Trino version `332-e.0`.

-----

## Adding New Modules (Tutorial)

Adding new modules is relatively simple, but there are a few important
guidelines to follow to ensure compatibility with the Minitrino CLI. The design
rules are the same for both catalogs and security modules. The example below
demonstrates the process of creating a new catalog module for a Postgres
service.

### Create the Module Directory

Create the module's directory in the `lib/modules/catalog/` directory:

```sh
mkdir lib/modules/catalog/postgres/
cd lib/modules/catalog/postgres/
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

**Note**: Passwords should always be `trinoRocks15` for consistency throughout
modules.

-----

### Add the Docker Compose YAML

In `lib/modules/catalog/postgres/`, add a Docker Compose file:

```sh
touch postgres.yml
```

Notice the naming convention: `postgres.yml`. Giving the same root name of
"postgres" to both the parent directory `postgres/` and to the Docker Compose
file `postgres.yml` will allow Minitrino to find our new catalog module.

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

The `metadata.json` file allows Minitrino to obtain key information for the
module. It is required for a module to work with the CLI.

In `lib/modules/catalog/postgres/`, add the `metadata.json` file:

```sh
bash -c 'cat << EOF > metadata.json
{
  "description": "Creates a Postgres catalog using the standard Postgres connector.",
  "incompatibleModules": [],
  "dependentModules": []
}
EOF'
```

The metadata file is presentable to the user via the `modules` command. The
`incompatibleModules` key restricts certain modules from being provisioned
alongside the given module. The `*` wildcard is a supported convention if the
module is incompatible with all other modules. Lastly, the `dependentModules`
key can be used to require other pre-defined modules to provision alongside the
module containing the `metadata.json` file.

### Add a Readme File

This step is not required for personal development, but it is required to commit
a module to the Minitrino repository.

In `lib/modules/catalog/postgres/`, add the `readme.md` file:

```sh
touch readme.md
```

This file should contain an overview of the module.

### Review Progress

The resulting directory tree should look like this (from the `/modules/catalog/`
directory):

```
postgres
├── metadata.json
├── postgres.yml
├── readme.md
└── resources
    ├── postgres
    │   └── postgres.env
    └── trino
        └── postgres.properties
```

### Configure the Docker Compose YAML File

We will now define the `postgres.yml` Docker Compose file. Set it up as follows,
and **read the important notes after**:

```yaml
version: "3.8"
services:

  trino:
    volumes:
    # Always place Trino files in `/etc/starburst/` as symbolic links can change between versions
      - "./modules/catalog/postgres/resources/trino/postgres.properties:/etc/starburst/catalog/postgres.properties"

  postgres:
    image: "postgres:${POSTGRES_VER}"
    container_name: "postgres"
    labels:
      - "com.starburst.tests=minitrino"
      - "com.starburst.tests.module.postgres=catalog-postgres"
    env_file:
      - "./modules/catalog/postgres/resources/postgres/postgres.env"

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

Secondly, notice how we applied sets of labels to the Postgres service. These
labels tell the CLI which resources to target when executing commands.

In general, there is no need to apply labels to the Trino service since they are
already applied in the parent Compose file **unless** the module is an extension
of the Trino service itself (i.e. the Snowflake modules). Labels should always
be applied to:

- Docker services (AKA the resulting container)
- Named volumes
- Images built from a Dockerfile

Labels should be defined in pairs of two. The convention is:

- The standard Minitrino resource label: `com.starburst.tests=minitrino`
- A module-specific resource label:
  `com.starburst.tests.module.<module-name>=<module-type>-<module-name>`
  - For this label, the `module-type` should be either `catalog` or `security`
  - This applies a unique label to the module, allowing it to be an isolated
    component when necessary.

In Compose files where multiple services are defined, all services should be
labeled with the same label sets (see `hive-s3.yml` for an example).

-----

**Note**: A named volume is defined explicitly in the Compose file, and these
should always have label sets applied to them. Below is an example of the
Compose file we just created with a named volume.

-----

```yaml
version: "3.8"
services:

  trino:
    volumes:
      - "./modules/catalog/postgres/resources/trino/postgres.properties:/etc/starburst/catalog/postgres.properties"

  postgres:
    image: "postgres:${POSTGRES_VER}"
    container_name: "postgres"
    labels: # These labels are applied to the service/container
      - "com.starburst.tests=minitrino"
      - "com.starburst.tests.module.postgres=catalog-postgres"
    env_file:
      - "./modules/catalog/postgres/resources/postgres/postgres.env"

volumes:
  postgres-data:
    labels: # These labels are applied to the named volume
      - "com.starburst.tests=minitrino"
      - "com.starburst.tests.module.postgres=catalog-postgres"
```

-----

**Note**: Certain modules will only extend the parent Trino service and do not
actually define any new services/containers. See the Snowflake catalog modules
for an example of this. For these modules, the only label requirement is to add
the module-specific label to the Trino service in the relevant
`docker-compose.yml` file

-----

### Test the New Catalog

We are all finished up. We can test our new catalog through the Minitrino CLI:

```sh
minitrino provision -m postgres
```

We can now shell into the `trino` container and run some tests:

```
docker exec -it trino bash 
trino-cli
trino> show catalogs;
```

### Customizing Images

If you need to build an image from a local Dockerfile, you can do so and
structure the Compose file accordingly. See the library's root
`docker-compose.yml` file for an example of this. Path references for volumes
and the image build context will follow the same convention as volume mount
paths described earlier.

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
version: "3.8"
services:

  trino:
    environment:
      MINITRINO_BOOTSTRAP: "bootstrap.sh"
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

Many modules can change the Trino `config.properties` and `jvm.config` files.
Because of this, there are two supported ways to modify these files with
Minitrino.

The first way is by setting the relevant environment variables in your
`module.yml` Docker Compose file. This will propagate the configs to the Trino
container when it is provisioned. For example:

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

The second way to modify these configuration files is via module [bootstrap
scripts](#bootstrap-scripts).

-----

## Troubleshooting

- If you experience issues executing a Minitrino command, re-run it with the
  `-v` option for verbose output. This will often reveal the issue
- If you experience an issue with a particular Docker container, consider
  running these commands:
  - `docker logs <container>`: Print the logs for a given container to the
    terminal
  - `docker ps`: Show all running Docker containers and associated statistics
  - `docker inspect <container>` to see various details about a container
- If you experience issues with a library module, check that that module is
  structured correctly according to the [module
  tutorial](#adding-new-modules-tutorial), and ensure the library and the CLI
  versions match
- Sometimes, a lingering persistent volume can cause problem (i.e. a stale Hive
  metastore database volume from a previous module), so you can run:
  - `minitrino down`
  - `minitrino -v remove --volumes` to remove **all** existing Minitrino
    volumes. Alternatively, run `minitrino -v remove --volumes --label <your
    label>` to specify a specific module for which to remove volumes. See the
    [removing resources](#removing-resources) section for more information.

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
