# Minipresto
A tool that makes it easy to run modular Presto environments locally.

[![Build Status](https://travis-ci.org/jefflester/minipresto.svg?branch=master)](https://travis-ci.org/jefflester/minipresto)
[![Presto Slack](https://img.shields.io/static/v1?logo=slack&logoColor=959DA5&label=Slack&labelColor=333a41&message=join%20conversation&color=3AC358)](https://prestosql.io/slack.html)
[![Presto: The Definitive Guide book download](https://img.shields.io/badge/Presto%3A%20The%20Definitive%20Guide-download-brightgreen)](https://www.starburstdata.com/oreilly-presto-guide-download/)

## Overview
- [Requirements](#requirements)
- [Installation](#installation)
- [CLI](#cli)
  - [Sample Commands](#sample-commands)
  - [Environment Variables](#environment-variables)
  - [Config File](#config-file)
  - [Config Environment Variables](#config-environment-variables)
- [Project Structure](#project-structure)
- [Adding New Modules (Tutorial)](#adding-new-modules-tutorial)

-----

## Requirements
- Docker 19.03.12+
- Docker Compose 1.26.2+
- Python 3.6+
- Pip
- Unix OS

-----

## Installation
You must first install the software requirements above. Once you have done that, run `./install.sh` to install the Minipresto CLI. If you encounter errors during installation, run `sudo -H ./install.sh -v`.

-----

## CLI
Minipresto is built with [Click](https://click.palletsprojects.com/en/7.x/), a popular open-source project used to build Python-based CLIs. Minipresto makes use of the Docker SDK and the `subprocess` module for much of its functionality.

Minipresto commands are documented below. Note that most command options can be specified with a shorthand alternative, which is the first letter of the each option, i.e. `--catalog` can be `-c`.

### Provisioning Environments
You can provision an environment via the `provision` command.

- `provision`: Executes a `docker-compose` command and brings up an environment. 
  - `--catalog`: Catalog module to provision. Can be none, one, or many.
  - `--security`: Security module to provision. Can be none, one, or many.
  - `--env`: Add or override environment variables. If any of the variables overlap with variables in the library's `.env` file or the `minipresto.cfg` file, the variable will be overridden with what is provided in `--env`. Can be none, one, or many.
  - `--no-rollback`: Will not rollback provisioned resources in the event of an error. Defaults to `False`.
  - `--docker-native`: Appends the constructed Compose command with native Docker Compose CLI options. Can be none, one, or many. To use this, simply pass in additional Docker Compose options, i.e. `minipresto provision --docker-native '--remove-orphans --force-recreate'` or `minipresto provision -d --build`. 
    - When passing multiple parameters to this option, the list needs to be space-delimited and surrounded with double or single quotes.
- If no options are passed in, the CLI will provision a standalone Presto container.
- The command cannot currently be used to append additional modules to an active environment. To modify an environment, first shut it down, then re-provision with the needed modules.

Sample `provision` commands:

```bash
minipresto provision --catalog hive-hms --catalog elasticsearch --security ldap --docker-native '--build --force-recreate'
minipresto provision -c hive-hms -c elasticsearch -s ldap -d '--build --force-recreate'
minipresto provision --env STARBURST_VER=332-e.6
```

This command constructs a Docker Compose command and executes it in the host shell. The commands look loosely similar to something like the below:

```bash
ENV_VAR_1=SOMETHING ENV_VAR_2=SOMETHING ENV_VAR_3=${ENV_VAR_3} ... \
docker-compose -f docker-compose.yml \
  -f modules/catalog/elasticsearch/elasticsearch.yml \
  -f modules/catalog/hive-hms/hive-hms.yml \
  -f modules/security/ldap/ldap.yml \
  up -d --build
```

### Removing Resources
You can remove resources with the `remove` command.

- `remove`: Removes any persistent resources associated with Minipresto environments. If no options are selected, **all** Minipresto resources are removed.
  - `--images`: Limit the removal to Minipresto images. 
  - `--volumes`: Limit the removal to Minipresto volumes. 
  - `--label`: Target a specific label for removal (requires a valid key-value pair). Can be used in combination with other options. Can be none, one, or many. Each label will be treated as a separate target for removal. 
  - `--force`: Forces the removal of Minipresto resources. Defaults to `False`.
- Persistent volumes tied to any *existing* container cannot be forcibly removed, neither by Minipresto nor by the Docker CLI. A persistent volume tied to a stopped container cannot be removed.
- Images tied to stopped containers can be forcibly removed, but any image tied to a running container cannot be forcibly removed, neither by Minipresto nor by the Docker CLI.

Sample `remove` command:

```bash
minipresto -v remove --volumes --label com.starburst.tests.module.postgres=catalog-postgres --force
```

### Shutting Down Environments
You can shut down an active environment with the `down` command.

- `down`: Stops and removes all running Minipresto containers (exactly what `docker-compose down` does).
  - `--keep`: Prevents the removal from containers; with this flag, containers will only be stopped, preserving any unnamed container volumes. Defaults to `False`.

Sample `down` command:

```bash
minipresto down
```

### Taking Environment Snapshots
You can capture a snapshot both active and inactive environments with the `snapshot` command. 

- `snapshot`: creates a tarball of the current state of an active environment *or* a specified environment and places in the library's `snapshots/` directory. This is useful for environment reusability. To snapshot an active environment, leave out the `--catalog` and `--security` options. To snapshot an inactive environment, you must specify which modules are to be captured via the `--catalog` and/or `--security` options.
  - `--name`: Name of the resulting tarball file (required). Must be alphanumeric.
  - `--catalog`: Catalog module to snapshot. Can be none, one, or many. If provided, active resources will not be captured in the snapshot.
  - `--security`: Security module to snapshot. Can be none, one, or many. If provided, active resources will not be captured in the snapshot.
  - `--force`: Override a check to see if the resulting file already exists. Defaults to `False`.
  - `--no-scrub`: Overrides the default behavior of scrubbing sensitive data (access keys and passwords) from the user config file. Defaults to `False`.
- Minipresto will make a best-effort attempt to grab the corresponding `provision` command and place it in the resulting snapshot. This makes it much easier for others to reuse the environment and spin it up the same way you did originally.

Sample `snapshot` commands:

```bash
# Take a snapshot of an active environment (this will create a tarball 
# called `snapshot-t2533.tar.gz` in the library's `snapshots/` directory):
minipresto snapshot --name t2533

# Take a snapshot of an inactive environment
minipresto snapshot --name mysnap --catalog hive-hms --security ldap
```

### Manage Configuration
You can manage Minipresto configuration with the `config` command. 

- `config`: Manages configuration. Executing the command opens an existing config file for edits or creates a templated config file if it doesn't already exist. 
  - `--reset`: Recreates the user home `~/.minipresto/` directory and creates a config file. Defaults to `False`.

### Top-Level CLI Options
You can get help, enable verbose output, and change the runtime library directory for any command. 

- `--help`: displays a help menu for a specific command or for the entire CLI. 
- `--verbose`: logs verbose output. Can be useful for debugging purposes.
- `--lib-path`: changes the library directory for the command.

```bash
# Get overall help
minipresto --help

# Get command-specific help
minipresto [COMMAND] --help

# Enable verbose outout
minipresto --verbose [COMMAND] # -v works as well
```

### Minipresto Library
The CLI's library directory should always point to the directory that holds the modules and snapshots you intend to interact with. The library directory can be set one of three ways, listed below in the order of precedence:

1. The `--lib-dir` CLI option sets the library directory for the current command.
2. The `minipresto.cfg` configuration file sets the library directory via the `LIB_PATH` variable. 
3. The CLI source code is used to set the library directory and assumes the project is being run out of a cloned repository.

If you are running as a user without a cloned repository, it is advisable to provide a pointer to the library in Minipresto's configuration via the `LIB_PATH` variable.

### Environment Variables
Environment variables are defined in the `.env` file in the library root. The `.env` file can be adjusted and added to as necessary. Note that environment variable keys which have Bash variables assigned to their values are defined in the `minipresto.cfg` file. These variables are able to be propagated to any Docker container via container environment variables passed to the Compose command. Any variable can be overridden with the `provision` command's `--env` option.

### Config File
Permanent configuration is set in `~/.minipresto/minipresto.cfg`. Here, you can define your library path and set Docker environment variables. Docker Environment variables are passed to the provisioned modules when the variables are defined in the `minipresto.cfg` file.

The template `minipresto.cfg` file includes all of the keys for each available variable. If any of these variables have values, they will be registered as environment variables when the `provision` command executes its Docker Compose script, and they will become available as environment variables in their respective containers. This is able to support Presto Secrets. 

### Config Environment Variables
Below is a list of all valid environment variables. The majority of these are passed to properties files and registered via Presto Secrets.

CLI environment variables:
- LIB_PATH: the filesystem path of the Minipresto library.

Docker environment variables:
- DOCKER_HOST: the host of the Docker daemon. Required if Docker is located anywhere other than localhost.

Module environment variables:
- STARBURST_LIC_PATH: required if using licensed Starburst features. It can point to any valid license on your filesystem.
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

### Caveats 
- The `snapshot` command does not retain overridden environment variables since they can change during intermediate commands executed against a running environment. 
- Minipresto will not function on Windows.

-----

## Project Structure 
The suite is built around Docker Compose files and utilizes Docker's ability to [extend Compose files](https://docs.docker.com/compose/extends/#multiple-compose-files).

The Starburst Presto service is defined in a Compose file at the project root. All other services will look up in the directory tree in order to reference the parent Presto service. Therefore, it is required that we provide the fully-qualified path relative to the project's root `docker-compose.yml` file when defining Docker resources. For example, suppose you have the following directory structure:

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

The `postgres.yml` file looks like:

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

Notice that the build context for the Dockerfile and the volume we mount to the Starburst Presto service are not relative to the `lib/modules/catalog/postgres/` directory––it is relative to the parent directory which houses the top-level `docker-compose.yml` file. Also, notice the label––this label will be used to identify resources related to testing suite so that the client commands actually work.

### Presto Dockerfile
Minipresto modifies the Starburst Presto Docker image by adding the Presto CLI to the image, as well as by providing `sudo` to the `presto` user. This is required for certain bootstrap scripts (i.e. using `yum` to install packages in a Presto container for a module). This image is compatible with Starburst Presto images back to Starburst Enterprise Presto version `332-e.0`.

-----

## Adding New Modules (Tutorial)
Adding new modules is relatively simple, but there are a few important guidelines to follow to ensure compatibility with the Minipresto CLI. The design rules are the same for both catalogs and security modules. The best way to demonstrate this process is through a tutorial. The example below demonstrates the process of creating a new catalog module for Postgres.

### Create the Relevant Directory
Create the module's directory in the `lib/modules/catalog/` directory:

```sh
mkdir lib/modules/catalog/postgres/
cd lib/modules/catalog/postgres/
```

### Add Presto Resources 
All resources for a module go inside of a `resources/` directory within the module. Inside this directory, place Presto-specific resources into a `presto/` directory, then mount the resources to the Presto service defined in the root `docker-compose.yml` file. 

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

Notice the naming convention––`postgres.yml`. Giving the same root name of "postgres" to both the parent directory `postgres/` and to the Docker Compose file `postgres.yml` will allow Minipresto to find our new catalog module when it is provisioned. 

Next, add an environment file for the Postgres service. Non-Presto resources should go into their own directory, so create one for postgres:

```sh
mkdir resources/postgres/
```

In the newly-created directory, add an environment file which will register the variables in the Postgres container when spun up:

```sh
bash -c "cat << EOF > postgres.env
POSTGRES_USER=admin
POSTGRES_PASSWORD=prestoRocks15
POSTGRES_DB=minipresto
EOF"
```

This file will initialize Postgres with a database Minipresto, a user `presto`, and a password `prestoRocks15`.

### Review Progress 
The resulting directory tree should look like this (from the `/modules/catalog/` directory):

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
We will now define the `postgres.yml` Docker Compose file. Set it up as follows, and **read the important notes after**:

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
      - "./modules/catalog/postgres/postgres.env"
```

### Important Implementation Details: Paths and Labels
We can observe a few things about the Compose file we just defined.

#### Path References for Volumes and Build Contexts
First, the volumes we mount *are not relative to the Compose file itself*, they are relative to the base `docker-compose.yml` file in the project root. The same goes for build contexts, such as the one in the Elasticsearch Compose file. This is because the CLI extends Compose files, meaning that all path references in sub-Compose files need to be relative to the positioning of the base Compose file. The base Compose file is determined in the way you execute a Docker Compose command––the first Compose file referenced in the command becomes the base file, and that happens to be the `docker-compose.yml` file in the project root (this is how the CLI constructs these commands). 

If this is confusing, you can read more about it on the [Docker docs](https://docs.docker.com/compose/extends/#multiple-compose-files). 

#### Minipresto Docker Labels
Secondly, notice how we applied sets of labels to the Postgres service. These labels tell the CLI which resources to target when executing commands. In general, there is no need to apply a label to the Presto service since it is already applied in the base Compose file **unless** the module is an extension of the Presto service––see the notes below. Labels should always be applied to:

- Docker services (AKA the resulting container)
- Persistent storage volumes
- Images built from a Dockerfile

Labels should be defined in pairs of two. The covention is:

- The standard Minipresto resource label: `com.starburst.tests=minipresto`
- A module-specific resource label: `com.starburst.tests.module.<module-name>=<module-type>-<module-name>`
  - For this label, the `module-type` should be either `catalog` or `security`

The second label is used by both the `snapshot` and `remove` CLI commands. `snapshot` will read the `catalog-<module-name>` or `security-<module-name>` and limit its extract to those modules' directories. The naming convention for this label is as follows:

In Compose files where multiple services are defined, all services should be labeled with the same label sets (see `hive-hms.yml` for an example).

In general, we always want to apply labels to:

-----

**Note**: A persistent volume is defined differently than normal volumes, and these should always have label sets applied to them. Below is an example of the Compose file we just created with a persistent volume.

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
      - "./modules/catalog/postgres/postgres.env"

volumes:
  postgres-data:
    labels: # These labels are applied to the persistent volume
      - "com.starburst.tests=minipresto"
      - "com.starburst.tests.module.postgres=catalog-postgres"
```

-----

**Note**: Certain modules will only extend the parent Presto service and do not actually define any new services. See the Snowflake catalog modules for an example of this. For these modules, the only label requirement is to add the standard, module-specific label sets to the Presto service in the relevant `module.yml` file 

-----

### Test the New Catalog
We are all finished up. We can test our new catalog through the Minipresto CLI:

```sh
minipresto provision --catalog postgres
```

We can now shell into the `presto` container and run some tests:

```
docker exec -it presto bash 
presto
presto> show catalogs;
```

### Customizing Images
If you need to build a custom image, you can do so and structure the Compose file accordingly. See the library's root `docker-compose.yml` file for an example of this.

### Bootstrap Scripts
Minipresto supports container bootstrap scripts. These scripts **do not replace** the entrypoint (or default command) for a given container. The script is copied from the Minipresto library to the container, executed, and then removed from the container. Containers are restarted after each bootstrap script execution, **so the bootstrap scripts themselves should not restart the container**.

If a bootstrap script has executed in a container and the unnamed volume associated with the container still exists, Minipresto will not re-execute the bootstrap script unless the contents of the script have changed. The is useful after running `minipresto down --keep` (which does not remove unnamed volumes associated with the containers), so that the subsequent provisioning command will not re-execute the same bootstrap script(s).

If a bootstrap script is updated, it is recommended to destroy the associated container(s) via `minipresto down` and then to re-provision.

To add a bootstrap script, simply add a `resources/bootstrap/` directory in any given module, create a shell script, and then reference the script name in the Compose YAML file:

```yaml
version: "3.7"
services:

  presto:
    environment:
      MINIPRESTO_BOOTSTRAP: "bootstrap.sh"
```

### Managing Presto's `config.properties` File
Since numerous modules can change the `config.properties` file, it is highly recommended to **not** mount a `config.properties` file to the Presto container, but instead to modify the file via the supported bootstrap script functionality. An example bootstrap snippet can be found below:

```bash
#!/usr/bin/env bash

set -euxo pipefail

echo "Adding Presto configs..."
cat <<EOT >> /usr/lib/presto/etc/config.properties
query.max-stage-count=105
query.max-execution-time=100h
query.max-execution-time=1h
EOT
```

Every time the `provision` command is executed, Minipresto will check for duplicate properties in `config.properties` and warn the user if they are present. The above script would warn the user about the duplicate key `query.max-execution-time`.
