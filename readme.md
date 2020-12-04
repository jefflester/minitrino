# Minipresto
A command line tool that makes it easy to run modular Presto environments
locally.

[![PyPI version](https://badge.fury.io/py/minipresto.svg)](https://badge.fury.io/py/minipresto)
[![Build Status](https://travis-ci.org/jefflester/minipresto.svg?branch=master)](https://travis-ci.org/jefflester/minipresto)
[![Presto Slack](https://img.shields.io/static/v1?logo=slack&logoColor=959DA5&label=Slack&labelColor=333a41&message=join%20conversation&color=3AC358)](https://prestosql.io/slack.html)
[![Presto: The Definitive Guide book download](https://img.shields.io/badge/Presto%3A%20The%20Definitive%20Guide-download-brightgreen)](https://www.starburstdata.com/oreilly-presto-guide-download/)

-----

**Latest Stable Release**: 1.0.1

-----

## Overview
- [Requirements](#requirements)
- [Installation](#installation)
- [CLI](#cli)
  - [Top-Level CLI Options](#top-level-cli-options)
  - [Provisioning Environments](#provisioning-environments)
  - [Removing Resources](#removing-resources)
  - [Shutting Down Environments](#shutting-down-environments)
  - [Taking Environment Snapshots](#taking-environment-snapshots)
  - [Manage User Configuration](#manage-user-configuration)
  - [Install the Library](#install-the-library)
  - [Display Module Metadata](#display-module-metadata)
  - [Display CLI Version](#display-cli-version)
  - [Pointing the CLI to the Minipresto Library](#pointing-the-cli-to-the-minipresto-library)
- [Minipresto Configuration File](#minipresto-configuration-file)
- [Project Structure](#project-structure)
- [Adding New Modules (Tutorial)](#adding-new-modules-tutorial)
- [Troubleshooting](#troubleshooting)
- [Reporting Bugs and Contributing](#reporting-bugs-and-contributing)

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
Minipresto is available on PyPI and the library is available for public download
on GitHub. To install the Minipresto CLI, run `pip install minipresto`. To
install the library, run `minipresto lib_install`.

### Developers
In the project's root, run `./install.sh` to install the Minipresto CLI. If you
encounter errors during installation, try running `sudo -H ./install.sh -v`.

-----

## CLI
Minipresto is built with [Click](https://click.palletsprojects.com/en/7.x/), a
popular, open-source toolkit used to build Python-based CLIs.

All Minipresto commands/options are documented below. Note that many command
options can be specified with a shorthand alternative, which is the first letter
of each option, i.e. `--module` can be `-m`.

### Top-Level CLI Options
You can get help, enable verbose output, and change the runtime library
directory for any command. 

```
Usage: minipresto [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose   Enable verbose output.
  -e, --env TEXT  Add or override environment variables.
                  
                  Environment variables are sourced from the Minipresto
                  library's root 'minipresto.env' file as well as the user 
                  config file in '~/.minipresto/minipresto.cfg'. Variables 
                  supplied by this option will override values from either 
                  of those sources. The variables will also be passed to the
                  environment of the shell executing commands during the
                  'provision' command.

  --help          Show this message and exit.
```

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
minipresto provision \
  --module hive-s3 \
  --module elasticsearch \
  --module ldap \
  --docker-native '--build --force-recreate'

minipresto provision -m hive-s3 -m elasticsearch -m ldap

minipresto --env STARBURST_VER=332-e.6 provision
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

Using the structure of the Minipresto library, it is able to merge multiple
Docker Compose files together.

#### Environment Variables
Environment variables passed to Docker containers are sourced through two
locations. The first is from the `minipresto.env` file in the library root. These
variables define the versions of the provisioned Docker services. The second is
from from variables set in the `[MODULES]` section of the `minipresto.cfg` file.
These variables can contain sensitive information like access credentials, so
their values are intentionally left out of library files.

Any existing environment variable can be overridden with the top-level `--env`
option, and any unset variable can be set with it.

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
minipresto -v remove \
  --volumes \
  --label com.starburst.tests.module.postgres=catalog-postgres \
  --force
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
  -r, --reset  Reset the Minipresto user configuration file and create a new
               config file from a template.
               
               WARNING: This will remove your configuration file (if it
               exists) and replace it with a template.

  --help       Show this message and exit.
```

### Install the Library
You can install the Minipresto library with the `lib_install` command. 

```
Usage: minipresto lib_install [OPTIONS]

  Install the Minipresto library.

Options:
  -v, --version TEXT  The version of the library to install.
  --help              Show this message and exit.
```

### Display Module Metadata
You can see Minipresto module metadata with the `modules` command. 

```
Usage: minipresto modules [OPTIONS]

  Display module metadata.

Options:
  -m, --module TEXT  A specific module to display metadata for.
  -j, --json         Print the resulting metadata in JSON form (shows
                     additional module metadata).

  -r, --running      Print metadata for all running modules.
  --help             Show this message and exit.
```

### Display CLI Version
You can display the Minipresto CLI version with the `version` command. 

```
Usage: minipresto version [OPTIONS]

  Display the Minipresto version.

Options:
  --help  Show this message and exit.
```

### Pointing the CLI to the Minipresto Library
The Minipresto CLI should always point to a compatible library with the expected
structure. The library directory can be set one of four ways, listed below in
the order of precedence:

1. Passing the `LIB_PATH` variable to the CLI's `--env` option sets the library
   directory for the current command.
2. The `minipresto.cfg` file's `LIB_PATH` variable sets the library directory if
   present.
3. The path `~/.minipresto/lib/` is used as the default lib path if the
   `LIB_PATH` var is not found.
4. As a last resort, Minipresto will check to see if the library exists in
   relation to the positioning of the `components.py` file and assumes the
   project is being run out of a cloned repository.

If you not running out of a cloned repository, it is advisable to provide a
pointer to the library in Minipresto's configuration via the `LIB_PATH` config.

-----

## Minipresto Configuration File
Sticky configuration is set in `~/.minipresto/minipresto.cfg`. The sections in
this file each serve a separate purpose.

### [CLI] Section
These configs allow the user to customize the behavior of Minipresto. 

- LIB_PATH: The filesystem path of the Minipresto library (specifically to the
  `lib/` directory).
- TEXT_EDITOR: The text editor to use with the `config` command, e.g. "vi",
  "nano", etc. Defaults to the shell's default editor.

### [DOCKER] Section
These configs allow the user to customize how Minipresto uses Docker.

- DOCKER_HOST: A URL pointing to an accessible Docker host. This is
  automatically detected by Docker otherwise.

### [PRESTO] Section
These configs allow the user to propagate config to the Presto container. Since
many modules can append to Presto's core files, the supported way to make
propagate changes to these Presto files is with these configs.

- CONFIG: Configuration for Presto's `config.properties` file. 
- JVM_CONFIG: Configuration for Presto's `jvm.config` file.

A multiline example of this section (note the indentation):

```
[PRESTO]
CONFIG=
    query.max-memory-per-node=500MB
    query.max-total-memory-per-node=500MB
JVM_CONFIG=
    -Dsun.security.krb5.debug=true
```

### [MODULES] Section
This section sets environment variables passed to containers provisioned by
Minipresto. Environment variables are only passed to a container if the variable
is specified in the module's `docker-compose.yml` file.

Variables propagated to the Presto container are supported by Presto secrets.

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

A simplified library structure:

```
lib
├── Dockerfile
├── docker-compose.yml
├── minipresto.env
├── modules
│   ├── catalog
│   │   └── postgres
│   │       ├── metadata.json
│   │       ├── postgres.yml
│   │       ├── readme.md
│   │       └── resources
│   │           ├── postgres
│   │           │   └── postgres.env
│   │           └── presto
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
│               └── presto
│                   ├── event-listener.properties
│                   └── postgres_event_logger.properties
├── snapshots
└── version
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

Notice that the volume mount is not relative to the
`lib/modules/catalog/postgres/` directory––it is relative to the parent
directory which houses the top-level `docker-compose.yml` file. Also, notice the
labels––these labels will be used to identify Docker resources tied to
Minipresto modules so that the CLI commands actually work.

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
rules are the same for both catalogs and security modules. The example below
demonstrates the process of creating a new catalog module for a Postgres
service.

### Create the Module Directory
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

In the newly-created `resources/presto/` directory, add a properties file.

```sh
bash -c "cat << EOF > postgres.properties
connector.name=postgresql
connection-url=jdbc:postgresql://postgres:5432/minipresto
connection-user=admin
connection-password=prestoRocks15
EOF"
```

-----

**Note**: Passwords should always be `prestoRocks15` for consistency throughout
modules. 

-----

### Add the Docker Compose YAML
In `lib/modules/catalog/postgres/`, add a Docker Compose file:

```sh
touch postgres.yml
```

Notice the naming convention: `postgres.yml`. Giving the same root name of
"postgres" to both the parent directory `postgres/` and to the Docker Compose
file `postgres.yml` will allow Minipresto to find our new catalog module.

Next, add an environment file for the Postgres service. Non-Presto resources
should go into their own directory, so create one for postgres:

```sh
mkdir resources/postgres/
```

In the newly-created directory, add an environment file which will register the
variables in the Postgres container when it is provisioned:

```sh
bash -c "cat << EOF > postgres.env
POSTGRES_USER=admin
POSTGRES_PASSWORD=prestoRocks15
POSTGRES_DB=minipresto
EOF"
```

This file will initialize Postgres with a database `minipresto`, a user
`presto`, and a password `prestoRocks15`.

### Add a Metadata File
This step is not required for personal development, but it is required to commit
a module to the Minipresto repository.

In `lib/modules/catalog/postgres/`, add the `metadata.json` file:

```sh
bash -c 'cat << EOF > metadata.json
{
  "description": "Creates a Postgres catalog using the standard Postgres connector.",
  "incompatible_modules": []
}
EOF'
```

The metadata file is presentable to the user via the `modules` command, and the
`incompatible_modules` key restricts certain modules from being provisioned
alongside the given module. The `*` wildcard is a supported convention if the
module is incompatible with all other modules.

### Add a Readme File
This step is not required for personal development, but it is required to commit
a module to the Minipresto repository.

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
are relative to the base `docker-compose.yml` file in the library root. This is
because the CLI extends Compose files, meaning that all path references in child
Compose files need to be relative to the positioning of the parent Compose file.

The base Compose file is determined when you execute a Docker Compose
command––the first Compose file referenced in the command becomes the base file,
and that happens to be the `docker-compose.yml` file in the library root. This
is how Minipresto constructs these commands. 

If this is confusing, you can read more about extending Compose files on the
[Docker docs](https://docs.docker.com/compose/extends/#multiple-compose-files). 

#### Minipresto Docker Labels
Secondly, notice how we applied sets of labels to the Postgres service. These
labels tell the CLI which resources to target when executing commands.

In general, there is no need to apply labels to the Presto service since they
are already applied in the parent Compose file **unless** the module is an
extension of the Presto service itself (i.e. the Snowflake modules). Labels
should always be applied to:

- Docker services (AKA the resulting container)
- Named volumes
- Images built from a Dockerfile

Labels should be defined in pairs of two. The convention is:

- The standard Minipresto resource label: `com.starburst.tests=minipresto`
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
the module-specific label to the Presto service in the relevant
`docker-compose.yml` file 

-----

### Test the New Catalog
We are all finished up. We can test our new catalog through the Minipresto CLI:

```sh
minipresto provision -m postgres
```

We can now shell into the `presto` container and run some tests:

```
docker exec -it presto bash 
presto-cli
presto> show catalogs;
```

### Customizing Images
If you need to build an image from a local Dockerfile, you can do so and
structure the Compose file accordingly. See the library's root
`docker-compose.yml` file for an example of this. Path references for volumes
and the image build context will follow the same convention as volume mount
paths described earlier.

### Bootstrap Scripts
Minipresto supports container bootstrap scripts. These scripts **do not
replace** the entrypoint (or default command) for a given container. The script
is copied from the Minipresto library to the container, executed, and then
removed from the container. Containers are restarted after each bootstrap script
execution, **so the bootstrap scripts themselves should not restart the
container's service**.

If a bootstrap script has already executed in a container *and* the volume
associated with the container still exists, Minipresto will not re-execute the
bootstrap script *unless the contents of the script have changed*. The is useful
after running `minipresto down --keep` (which does not remove unnamed container
volumes), so that the subsequent `provision` command will not re-execute the
same bootstrap script(s).

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

The `elasticsearch` module is a good example of this.

### Managing Presto's `config.properties` File
Many modules can change the Presto `config.properties` and `jvm.config` files.
Because of this, there are two supported ways to modify these files with
Minipresto.

The first way is by setting the `CONFIG` variable in your `minipresto.cfg` file.
This will propagate the config to the Presto container when it is provisioned.

Generally speaking, this can be used for any type of configuration (i.e. memory
configuration) that is unlikely to be modified by any module. This also applies
to the `jvm.config` file, which has identical support via the `JVM_CONFIG`
variable. If there are duplicate configs in either file, Minipresto will warn
the user.

To set these configs, your configuration file should look like:

```
[PRESTO]
CONFIG=
    query.max-memory-per-node=500MB
    query.max-total-memory-per-node=500MB
JVM_CONFIG=
    -Dsun.security.krb5.debug=true
```

The second way to modify core Presto configuration is via module bootstrap
scripts. This method is utilized by modules that need to make module-specific
changes to Presto files. An example bootstrap snippet can be found below:

```bash
#!/usr/bin/env bash

set -euxo pipefail

echo "Adding Presto configs..."
cat <<EOT >> /usr/lib/presto/etc/config.properties
query.max-stage-count=105
query.max-execution-time=1h
EOT
```

-----

## Troubleshooting

- If you experience issues executing a Minipresto command, re-run it with the
  `-v` option for verbose output. This will often reveal the issue
- If you experience an issue with a particular Docker container, consider
  running these commands:
  - `docker logs <container>`: Print the logs for a given container to the
    terminal
  - `docker ps`: Show all running Docker containers and associated statistics
- If you experience issues with a library module, check that that module is
  structured correctly according to the [module
  tutorial](#adding-new-modules-tutorial)

If none of these troubleshooting tips help to resolve your issue, [please file a
GitHub issue](#reporting-bugs-and-contributing) and provide as much information
as possible.

-----

## Reporting Bugs and Contributing
To report bugs, please file a GitHub issue on the [Minipresto
repository](https://github.com/jefflester/minipresto). Bug reports should:

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
