# Minipresto
A command line tool that makes it easy to run modular Presto environments
locally.

[![Build Status](https://travis-ci.org/jefflester/minipresto.svg?branch=master)](https://travis-ci.org/jefflester/minipresto)
[![Presto Slack](https://img.shields.io/static/v1?logo=slack&logoColor=959DA5&label=Slack&labelColor=333a41&message=join%20conversation&color=3AC358)](https://prestosql.io/slack.html)
[![Presto: The Definitive Guide book download](https://img.shields.io/badge/Presto%3A%20The%20Definitive%20Guide-download-brightgreen)](https://www.starburstdata.com/oreilly-presto-guide-download/)

## Overview
- [Requirements](#requirements)
- [Installation](#installation)
- [CLI](#cli)
  - [Provisioning Environments](#provisioning-environments)
  - [Removing Resources](#removing-resources)
  - [Shutting Down Environments](shutting-down-environments)
  - [Taking Environment Snapshots](#taking-environment-snapshots)
  - [Manage User Configuration](#manage-user-configuration)
  - [Top-Level CLI Options](#top-level-cli-options)
  - [Minipresto Library](#Minipresto-library)
  - [Environment Variables](#environment-variables)
  - [Minipresto Configuration File](#minipresto-configuration-file)
- [Project Structure](#project-structure)
- [Adding New Modules (Tutorial)](#adding-new-modules-tutorial)

-----

## Requirements
- Docker 19.03.12+
- Docker Compose 1.26.2+
- Python 3.6+
- Pip
- Linux or Mac OS

-----

## Installation

### End Users
Minipresto is available on PyPy and the library is available for public download
on S3. To install the Minipresto CLI, run `pip install minipresto`. To install
the library, run `minipresto lib --install`.

### Developers
In the project's root, run `./install.sh` to install the Minipresto CLI. If you
encounter errors during installation, run `sudo -H ./install.sh -v`.

-----

## CLI
Minipresto is built with [Click](https://click.palletsprojects.com/en/7.x/), a
popular, open-source toolkit used to build Python-based CLIs.

All Minipresto commands/options are documented below. Note that many command
options can be specified with a shorthand alternative, which is the first letter
of each option, i.e. `--catalog` can be `-c`.

### Provisioning Environments
You can provision an environment via the `provision` command.

```
Usage: minipresto provision [OPTIONS]

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
                            
                            Example: minipresto provision --docker-native
                            --build
                            
                            Example: minipresto provision --docker-native '--
                            remove-orphans --force-recreate'

  --help                    Show this message and exit.
```

Notes:

- If no options are passed in, the CLI will provision a standalone Presto
  container.
- The command cannot currently be used to append additional modules to an active
  environment. To modify an environment, first shut it down, then re-provision
  with the needed modules.

Sample `provision` commands:

```bash
minipresto provision --module hive-s3 --module elasticsearch --module ldap --docker-native '--build --force-recreate'
minipresto provision -m hive-s3 -m elasticsearch -m ldap
minipresto --env STARBURST_VER=332-e.6 provision
```

The `provision` command constructs a Docker Compose command and executes it in
the host shell. The commands look like:

```bash
ENV_VAR_1=SOMETHING ENV_VAR_2=SOMETHING ENV_VAR_3=${ENV_VAR_3} ... \
docker-compose -f docker-compose.yml \
  -f modules/catalog/elasticsearch/elasticsearch.yml \
  -f modules/catalog/hive-s3/hive-s3.yml \
  -f modules/security/ldap/ldap.yml \
  up -d
```

Using the structure of the Minipresto library, it is able to merge multiple
Docker Compose files together.

#### Using Licensed Starburst Features
If you are using licensed features, you will need to provide a path to a valid
Starburst license. This can be set via `minipresto config` or provided via the
`--env` option at command runtime. The variable for this is
`STARBURST_LIC_PATH`. 

Additionally, you need to uncomment the volume mount in the library's root
`docker-compose.yml` file:

```yaml
  # Uncomment this to enable the volume mount. The variable should point to a
  # valid SEP license. 
  volumes:
    - "${STARBURST_LIC_PATH}:/usr/lib/presto/etc/starburstdata.license:ro"
```

### Removing Resources
You can remove resources with the `remove` command.

```
Usage: minipresto remove [OPTIONS]

  Remove Minipresto resources.

Options:
  -i, --images      Remove Minipresto images.
  -v, --volumes     Remove Minipresto container volumes.
  -l, --label TEXT  Target specific labels for removal (format: key-value
                    pair(s)).

  -f, --force       Force the removal of Minipresto resources. Normal Docker
                    removal restrictions apply.

  --help            Show this message and exit.
```

Notes:

- Named volumes tied to any *existing* container cannot be forcibly removed,
  neither by Minipresto nor by the Docker CLI/SDK.
- Images tied to stopped containers can be forcibly removed, but any image tied
  to a running container cannot be forcibly removed, neither by Minipresto nor
  by the Docker CLI.

Sample `remove` command:

```bash
minipresto -v remove --volumes --label com.starburst.tests.module.postgres=catalog-postgres --force
```

This will only remove volumes associated to the Postgres catalog module.

### Shutting Down Environments
You can shut down an active environment with the `down` command.

```
Usage: minipresto down [OPTIONS]

  Bring down running Minipresto containers. This command follows the
  behavior of `docker-compose down` where containers are both stopped and
  removed.

Options:
  -k, --keep  Does not remove containers; instead, containers will only be
              stopped.

  --sig-kill  Stop Minipresto containers without a grace period.
  --help      Show this message and exit.
```

Sample `down` command:

```bash
minipresto -v down
```

### Taking Environment Snapshots
You can capture snapshots for both active and inactive environments with the
`snapshot` command. 

```
Usage: minipresto snapshot [OPTIONS]

  Create a snapshot of a Minipresto environment. A tarball is placed in the
  Minipresto `lib/snapshots/` directory.

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
                        Defaults to the snapshots directory in the Minipresto
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

- Minipresto records the original `provision` command and places it in the
  snapshot file as `provision-snapshot.sh`; this can be directly executed. This
  makes it easier for others to reuse the environment and provision it
  identically.

Sample `snapshot` commands:

```bash
# Take a snapshot of an active environment (this will create a tarball 
# called `snapshot-t2533.tar.gz` in the library's `snapshots/` directory):
minipresto snapshot --name t-2533

# Take a snapshot of specific modules:
minipresto snapshot -n super-cool-env -m hive-s3 -m elasticsearch -m ldap
```

### Manage User Configuration
You can manage Minipresto configuration with the `config` command. 

```
Usage: minipresto config [OPTIONS]

  Edit the Minipresto user configuration file.

Options:
  -r, --reset  Reset the Minipresto user configuration directory and create a
               new config file.

               WARNING: This will remove your configuration file (if it
               exists) and replace it with a template.

  --help       Show this message and exit.
```

### Top-Level CLI Options
You can get help, enable verbose output, and change the runtime library
directory for any command. 

```
Usage: minipresto [OPTIONS] COMMAND [ARGS]...

  Welcome to the Minipresto command line interface.

  To report issues and ask questions, please file a GitHub issue and apply a
  descriptive label at the GitHub repository:
  https://github.com/jefflester/minipresto

Options:
  -v, --verbose   Enable verbose output.
  -e, --env TEXT  Add or override environment variables.

                  Environment variables are sourced from the Minipresto
                  library's root '.env' file as well as the user config file
                  in '~/.minipresto/minipresto.cfg'. Variables supplied by
                  this option will override values from either of those
                  sources. The variables will also be passed to the
                  environment of the shell executing commands during the
                  'provision' command.

  --help          Show this message and exit.
```

### Minipresto Library
The Minipresto CLI should always point to a compatible library with the expected
structure. The library directory can be set one of four ways, listed below in
the order of precedence:

1. Passing `LIB_PATH` to the CLI's `--env` option sets the library directory for
   the current command.
2. The `minipresto.cfg` file's `LIB_PATH` variable sets the library directory if
   present.
3. The path `~/.minipresto/lib/` is used as the default lib path if the
   `LIB_PATH` var is not found.
4. As a last resort, Minipresto will check to see if the library exists in
   relation to the positioning of the `components.py` file and assumes the
   project is being run out of a cloned repository.

If you not running out of a cloned repository, it is advisable to provide a
pointer to the library in Minipresto's configuration via the `LIB_PATH` config.

### Environment Variables
Environment variables are passed to the Docker Compose files through two
sources. The first is from the `.env` file in the library root. These variables
define the versions of the provisioned Docker services.

Environment variables can also be passed to Docker Compose files from variables
set in the `[MODULES]` section of the `minipresto.cfg` file. These can contain
sensitive information like access credentials, so their values are intentionally
left out of library files.

Any existing Docker Compose environment variable can be overridden with the
`provision` command's `--env` option, and any unset variable can be set with it.

### Minipresto Configuration File
Permanent configuration is set in `~/.minipresto/minipresto.cfg`. The sections
in this file each serve a separate purpose. Minipresto can function with none of
these configs set, but if you are not running out of a cloned repository, you
will need to point it to a valid library.

#### [CLI] Section
These configs allow the user to customize the behavior of Minipresto. 

- LIB_PATH: The filesystem path of the Minipresto library (specifically to the
  `lib/` directory).
- TEXT_EDITOR: The text editor to use with the `config` command, e.g. "vi",
  "nano", etc. Defaults to the shell's default editor.

#### [DOCKER] Section
These configs allow the user to customize how Minipresto uses Docker.

- DOCKER_HOST: A URL pointing to an accessible Docker host. This is
  automatically detected by Docker otherwise.

#### [PRESTO] Section
These configs allow the user to set global Presto configuration. Since many
modules can append to Presto's core files, the supported way to make global
changes to these files is with these configs.

- CONFIG: Configuration for Presto's `config.properties` file. 
- JVM_CONFIG: Configuration for Presto's `jvm.config` file.

A multiline example of this section:

```
[PRESTO]
CONFIG=
    query.max-memory-per-node=500MB
    query.max-total-memory-per-node=500MB
JVM_CONFIG=
    -Dsun.security.krb5.debug=true
```

#### [MODULES] Section
This section sets environment variables passed to containers provisioned by
Minipresto. Environment variables are only set in a container if it is specified
in the relevant `docker-compose.yml` file. This supports Presto secrets.

- STARBURST_LIC_PATH: Required if using licensed Starburst Enterprise Presto
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
to [extend Compose files](https://docs.docker.com/compose/extends/#multiple-compose-files).

The Starburst Presto service is defined in a Compose file at the library root,
and all other services look up in the directory tree to reference the parent
Presto service. In Compose files, the fully-qualified path––relative to the
library's root `docker-compose.yml` file––must be provided for Docker to locate
resources.

An abbreviated library structure:

```
lib
├── Dockerfile
├── docker-compose.yml
├── modules
│   ├── catalog
│   │   ├── postgres
│   │   │   ├── postgres.yml
│   │   │   ├── readme.md
│   │   │   └── resources
│   │   │       ├── postgres
│   │   │       │   └── postgres.env
│   │   │       └── presto
│   │   │           └── postgres.properties
│   │   ├── elasticsearch
│   │   │   ├── elasticsearch.yml
│   │   │   ├── readme.md
│   │   │   └── resources
│   │   │       ├── bootstrap
│   │   │       │   └── bootstrap-elasticsearch.sh
│   │   │       └── presto
│   │   │           └── elasticsearch.properties
│   ├── resources
│   └── security
└── snapshots
```

And the contents of a `docker-compose.yml` file (`postgres.yml`):

```yaml
version: "3.7"
services:

  presto:
    volumes:
      - "./modules/catalog/postgres/resources/presto/postgres.properties:/usr/lib/presto/etc/catalog/postgres.properties"

  postgres:
    image: "postgres:${POSTGRES_VER}"
    container_name: "postgres"
    labels:
      - "com.starburst.tests=minipresto"
      - "com.starburst.tests.module.postgres=catalog-postgres"
    env_file:
      - "./modules/catalog/postgres/resources/postgres/postgres.env"
```

Notice that the mounted volume is not relative to the
`lib/modules/catalog/postgres/` directory––it is relative to the parent
directory which houses the top-level `docker-compose.yml` file. Also, notice the
label––this label will be used to identify resources related to testing suite so
that the client commands actually work.

### Presto Dockerfile
Minipresto modifies the Starburst Presto Docker image by adding the Presto CLI
to the image as well as by providing `sudo` to the `presto` user. This is
required for certain bootstrap scripts (i.e. using `yum` to install packages in
a Presto container for a module). This image is compatible with Starburst Presto
images back to Starburst Presto version `332-e.0`.

-----

## Adding New Modules (Tutorial)
Adding new modules is relatively simple, but there are a few important
guidelines to follow to ensure compatibility with the Minipresto CLI. The design
rules are the same for both catalogs and security modules. The best way to
demonstrate this process is through a tutorial. The example below demonstrates
the process of creating a new catalog module for Postgres.

### Create the Relevant Directory
Create the module's directory in the `lib/modules/catalog/` directory:

```sh
mkdir lib/modules/catalog/postgres/
cd lib/modules/catalog/postgres/
```

### Add Presto Resources 
All resources for a module go inside of a `resources/` directory within the
module. Inside this directory, place Presto-specific resources into a `presto/`
directory, then mount the resources to the Presto service defined in the root
`docker-compose.yml` file. 

```sh
mkdir -p resources/presto/
```

In the newly-created `presto/` directory, add a properties file.

```sh
bash -c "cat << EOF > postgres.properties
connector.name=postgresql
connection-url=jdbc:postgresql://postgres:5432/minipresto
connection-user=admin
connection-password=prestoRocks15
EOF"
```

**Note**: Passwords should always be `prestoRocks15` for consistency. 

### Add the Docker Compose YAML
In `lib/modules/catalog/postgres/`, add a Docker Compose file:

```sh
touch postgres.yml
```

Notice the naming convention––`postgres.yml`. Giving the same root name of
"postgres" to both the parent directory `postgres/` and to the Docker Compose
file `postgres.yml` will allow Minipresto to find our new catalog module when it
is provisioned. 

Next, add an environment file for the Postgres service. Non-Presto resources
should go into their own directory, so create one for postgres:

```sh
mkdir resources/postgres/
```

In the newly-created directory, add an environment file which will register the
variables in the Postgres container when spun up:

```sh
bash -c "cat << EOF > postgres.env
POSTGRES_USER=admin
POSTGRES_PASSWORD=prestoRocks15
POSTGRES_DB=minipresto
EOF"
```

This file will initialize Postgres with a database Minipresto, a user `presto`,
and a password `prestoRocks15`.

### Review Progress 
The resulting directory tree should look like this (from the `/modules/catalog/`
directory):

```
postgres
├── postgres.yml
└── resources
    ├── postgres
    │   └── postgres.env
    └── presto
        └── postgres.properties
```

### Configure the Docker Compose YAML File
We will now define the `postgres.yml` Docker Compose file. Set it up as follows,
and **read the important notes after**:

```yaml
version: "3.7"
services:

  presto:
    volumes:
    # Always place Presto files in `/usr/lib/presto/etc/` as symbolic links can change between versions
      - "./modules/catalog/postgres/resources/presto/postgres.properties:/usr/lib/presto/etc/catalog/postgres.properties"

  postgres:
    image: "postgres:${POSTGRES_VER}"
    container_name: "postgres"
    labels:
      - "com.starburst.tests=minipresto"
      - "com.starburst.tests.module.postgres=catalog-postgres"
    env_file:
      - "./modules/catalog/postgres/resources/postgres/postgres.env"

```

### Important Implementation Details: Paths and Labels
We can observe a few things about the Compose file we just defined.

#### Path References for Volumes and Build Contexts
First, the volumes we mount *are not relative to the Compose file itself*, they
are relative to the base `docker-compose.yml` file in the project root. The same
goes for build contexts, such as the one in the Elasticsearch Compose file. This
is because the CLI extends Compose files, meaning that all path references in
sub-Compose files need to be relative to the positioning of the parent Compose
file. The base Compose file is determined when you execute a Docker Compose
command––the first Compose file referenced in the command becomes the base file,
and that happens to be the `docker-compose.yml` file in the project root. This
is how the Minipresto constructs these commands. 

If this is confusing, you can read more about it on the [Docker
docs](https://docs.docker.com/compose/extends/#multiple-compose-files). 

#### Minipresto Docker Labels
Secondly, notice how we applied sets of labels to the Postgres service. These
labels tell the CLI which resources to target when executing commands. In
general, there is no need to apply a label to the Presto service since it is
already applied in the base Compose file **unless** the module is an extension
of the Presto service––see the notes below. Labels should always be applied to:

- Docker services (AKA the resulting container)
- Named volumes
- Images built from a Dockerfile

Labels should be defined in pairs of two. The convention is:

- The standard Minipresto resource label: `com.starburst.tests=minipresto`
- A module-specific resource label:
  `com.starburst.tests.module.<module-name>=<module-type>-<module-name>`
  - For this label, the `module-type` should be either `catalog` or `security`

The second label is used by both the `snapshot` and `remove` CLI commands.
`snapshot` will read the `catalog-<module-name>` or `security-<module-name>` and
limit its extract to those modules' directories. The naming convention for this
label is as follows:

In Compose files where multiple services are defined, all services should be
labeled with the same label sets (see `hive-s3.yml` for an example).

In general, we always want to apply labels to:

- Images that are built by Dockerfiles (see the root `docker-compose.yml` file)
- Services/containers defined in Docker Compose files 
- Named volumes defined in Docker Compose files

-----

**Note**: A named volume is defined explicitly in the Compose file, and these
should always have label sets applied to them. Below is an example of the
Compose file we just created with a named volume.

-----

```yaml
version: "3.7"
services:

  presto:
    volumes:
      - "./modules/catalog/postgres/resources/presto/postgres.properties:/usr/lib/presto/etc/catalog/postgres.properties"

  postgres:
    image: "postgres:${POSTGRES_VER}"
    container_name: "postgres"
    labels: # These labels are applied to the service/container
      - "com.starburst.tests=minipresto"
      - "com.starburst.tests.module.postgres=catalog-postgres"
    env_file:
      - "./modules/catalog/postgres/resources/postgres/postgres.env"

volumes:
  postgres-data:
    labels: # These labels are applied to the named volume
      - "com.starburst.tests=minipresto"
      - "com.starburst.tests.module.postgres=catalog-postgres"
```

-----

**Note**: Certain modules will only extend the parent Presto service and do not
actually define any new services/containers. See the Snowflake catalog modules
for an example of this. For these modules, the only label requirement is to add
the standard, module-specific label sets to the Presto service in the relevant
`docker-compose.yml` file 

-----

### Test the New Catalog
We are all finished up. We can test our new catalog through the Minipresto CLI:

```sh
minipresto provision --catalog postgres
```

We can now shell into the `presto` container and run some tests:

```
docker exec -it presto bash 
presto-cli
presto> show catalogs;
```

### Customizing Images
If you need to build a custom image, you can do so and structure the Compose
file accordingly. See the library's root `docker-compose.yml` file for an
example of this.

### Bootstrap Scripts
Minipresto supports container bootstrap scripts. These scripts **do not
replace** the entrypoint (or default command) for a given container. The script
is copied from the Minipresto library to the container, executed, and then
removed from the container. Containers are restarted after each bootstrap script
execution, **so the bootstrap scripts themselves should not restart the
container's service**.

If a bootstrap script has already executed in a container *and* the unnamed
volume associated with the container still exists, Minipresto will not
re-execute the bootstrap script *unless the contents of the script have
changed*. The is useful after running `minipresto down --keep` (which does not
remove unnamed container volumes), so that the subsequent provisioning command
will not re-execute the same bootstrap script(s).

If a bootstrap script is updated, it is recommended to destroy the associated
container(s) via `minipresto down` and then to re-provision.

To add a bootstrap script, add a `resources/bootstrap/` directory in any given
module, create a shell script, and then reference the script name in the Compose
YAML file:

```yaml
version: "3.7"
services:

  presto:
    environment:
      MINIPRESTO_BOOTSTRAP: "bootstrap.sh"
```

### Managing Presto's `config.properties` File
Many modules can change the Presto `config.properties` and `jvm.config` files.
Because of this, there are two supported ways to modify these files with
Minipresto.

The first way is by setting the `CONFIG` variable in your `minipresto.cfg` file.
This is intended to set global Presto configuration that will be present for any
module. Generally speaking, this can be used for any type of configuration (i.e.
memory configuration) that is not likely to be modified by any module. This also
applies to the `jvm.config` file, which has identical support via the
`JVM_CONFIG` variable. 

To set these variables, your configuration file should
look like:

```
[PRESTO]
CONFIG=
    query.max-memory-per-node=500MB
    query.max-total-memory-per-node=500MB
JVM_CONFIG=
    -Dsun.security.krb5.debug=true
```

The second way to modify core Presto configuration is via bootstrap scripts.
This method is utilized by modules that need to make module-specific changes to
Presto files. An example bootstrap snippet can be found below:

```bash
#!/usr/bin/env bash

set -euxo pipefail

echo "Adding Presto configs..."
cat <<EOT >> /usr/lib/presto/etc/config.properties
query.max-stage-count=105
query.max-execution-time=1h
EOT
```
