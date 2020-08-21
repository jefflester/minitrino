# Minipresto
A tool that makes it easy to run modular Presto environments locally.

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
- [Developer Notes](#developer-notes)

-----

## Requirements
- Docker 
- Docker Compose
- Python 3.6+
- Pip
- Unix OS

-----

## Installation
You must first install the software requirements above. Once you have done that, you can run `./install.sh` to install the `minipresto` CLI (add `-v` for verbose output). If you receive permissions errors, run `sudo -H ./install.sh -v`.

-----

## CLI
The `minipresto` CLI is built with [Click](https://click.palletsprojects.com/en/7.x/), a popular open-source project for constructing Python CLI tools. The CLI accepts a variety of commands/options and either executes them via the Docker SDK or as shell commands via the Python `subprocess` module.

The following commands are available to the `minipresto` CLI (**almost all** options can be specified with a shorthand alternative, which is the first letter of the each option, i.e. `--catalog` can be `-c`):

### Provisioning Environments
You can provision an environment via the `provision` command.

- `provision`: Builds a `docker-compose` command string, executes that via `subprocess`, and brings up an environment. 
  - `--catalog`: Catalog module to provision. Can be none, one, or many.
  - `--security`: Security module to provision. Can be none, one, or many.
  - `--env`: Override an existing environment variable in the root `.env` file. Can be none, one, or many.
  - `--docker-native`: Appends the constructed Compose command with native Docker Compose CLI options. Can be none, one, or many. To use this, simply pass in additional Docker Compose options, i.e. `minipresto provision --docker-native '--remove-orphans --force-recreate'` or `minipresto provision -d --build`. 
    - When passing multiple parameters to this option, the list needs to be space-delimited and surrounded with double or single quotes.
- If no options are passed in, the CLI will provision a standalone Presto container.
- The command cannot currently be used to append additional modules to an active environment. To modify an environment, first shut it down, then reprovision with the needed modules.

### Removing Resources
You can remove resources with the `remove` command.

- `remove`: Removes any persistent resources associated with `minipresto` environments. If no options are selected, all `minipresto` resources are removed.
  - `--images`: Limit the removal to `minipresto` images. 
  - `--volumes`: Limit the removal to `minipresto` volumes. 
  - `--label`: Target a specific label for removal (requires a valid key-value pair). Can be used in combination with other options. Can be none, one, or many. Each label passed in will be treated as a separate target for removal. 
  - `--force`: Forces the removal of `minipresto` resources. Defaults to `False`.
- Persistent volumes tied to any *existing* container cannot be forcibly removed, neither by the `minipresto` CLI nor the `docker` CLI. A persistent volume tied to a stopped container cannot be removed.
- Images tied to stopped containers can be forcibly removed, but any image tied to a running container cannot be forcibly removed, neither by the `minipresto` CLI not the `docker` CLI.

### Shutting Down Environments
You can shut down an active environment with the `down` command.

- `down`: Stops and removes all running `minipresto` containers (exactly what `docker-compose down` does).

### Taking Environment Snapshots
You can capture a snapshot both active and inactive environments with the `snapshot` command. 

- `snapshot`: creates a tarball of the current state of an active environment *or* a specified environment and places in the library's `snapshots/` directory. This is useful for environment reusability. To snapshot an active environment, leave out the `--catalog` and `--security` options. To snapshot an inactive environment, you must specify which modules are to be captured via the `--catalog` and/or `--security` options.
  - `--name`: Name of the resulting tarball file (required). Must be alphanumeric.
  - `--catalog`: Catalog module to snapshot. Can be none, one, or many. If provided, active resources will not be captured in the snapshot.
  - `--security`: Security module to snapshot. Can be none, one, or many. If provided, active resources will not be captured in the snapshot.
  - `--force`: Override a check to see if the resulting file already exists. Defaults to `False`.
  - `--no-scrub`: Overrides the default behavior of scrubbing sensitive data (access keys and passwords) from the user config file. Defaults to `False`.
- The CLI will make a best-effort attempt to grab the corresponding `provision` command and place it in the resulting snapshot. This makes it much easier for others to reuse the environment and spin it up the same way you did originally.

### Manage Configuration
You can manage `minipresto` configuration with the `config` command. 

- `config`: Manages configuration. Executing the command opens an existing config file for edits or creates a templated config file if it doesn't already exist. 
  - `--reset`: Recreates the user home `.minipresto` directory and creates a config file. Defaults to `False`.

### Top-Level CLI Options
You can get help, enable verbose output, and change the runtime library directory for any command. 

- `--help`: displays a help menu for a specific command or for the entire CLI. 
- `--verbose`: logs verbose output. Can be useful for debugging purposes.
- `--lib-path`: changes the library directory for the command.

### Library Path/Directory 
The CLI's library directory should always point to the directory that holds the modules and snapshots you intend to interact with. The library directory can be set one of three ways. The three options follow an order of precedence, and they are listed below:

1. The `--lib-dir` CLI option sets the library directory for the current command.
2. The `minipresto.cfg` configuration file sets the library directory if present. 
3. The project root is used to set the library directory and assumes the project is being run out of a cloned repository. 

If you are running as a user without the entire repository, it is advisable to provide a pointer in `~/.minipresto/minipresto.cfg`.

### Sample Commands
Get help for the entire CLI:

```sh
minipresto --help
```

Get help for a specific command:

```sh
minipresto config --help
```

Enable verbose output:

```sh
minipresto --verbose provision --catalog ...
```

Provision Hive, Elasticsearch, and LDAP modules, and build any changes to any of the modules' Dockerfiles:

```sh
minipresto provision --catalog hive-hms elasticsearch --security ldap -d --build
```

For the above command, this will be executed in a Python subprocess:

```sh
ENV_VAR_1=SOMETHING ENV_VAR_2=SOMETHING ENV_VAR_3=${ENV_VAR_3} ... \
docker-compose -f docker-compose.yml \
  -f modules/catalog/elasticsearch/elasticsearch.yml \
  -f modules/catalog/hive-hms/hive-hms.yml \
  -f modules/security/ldap/ldap.yml \
  up -d --build
```

Provision an environment with native Docker Compose options:

```sh
minipresto provision --catalog hive-hms --docker-native --remove-orphans
```

Shut down an active environment with verbose output:

```sh
minipresto -v down
```

Take a snapshot of an active environment (this will create a tarball called `snapshot-t2533.tar.gz` in the repository's `snapshots/` directory):

```sh
minipresto snapshot --name t2533
```

Remove all `minipresto` resources:

```sh
minipresto remove
```

Forcibly remove `minipresto` volumes according to the label that is passed in:

```sh
minipresto -v remove --volumes --label com.starburst.tests.module.postgres=catalog-postgres --force
```

### Environment Variables
Environment variables are defined in the `.env` file in the project root. The `.env` file can be adjusted and added to as necessary. Note that environment variable keys which have Bash variables assigned to their values are defined in the `minipresto.cfg` file in `~/.minipresto/`. These special variables are able to be propagated to any Docker container via container environment variables (see the root `docker-compose.yml` file for an example) passed to the Compose command.

### Config File
Permanent configuration is set in `~/.minipresto/minipresto.cfg`. Here, you can define your library path and set Docker environment variables. Docker Environment variables are passed to the provisioned modules when the variables are defined in the `minipresto.cfg` file.

The template `minipresto.cfg` file includes all of the keys for each available variable. If any of these variables have values, they will be registered as environment variables when the `provision` command executes its Docker Compose script, and they will become available as environment variables in their respective containers. This is able to support Presto Secrets. 

### Config Environment Variables
Below is a list of all valid environment variables. The majority of these are passed to properties files and registered via Presto Secrets.

- STARBURST_LIC_PATH
  - This is required if using licensed Starburst features. It can point to any valid license on your filesystem.
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
- LDAP_ORGANISATION
- LDAP_DOMAIN
- LDAP_ADMIN_PASSWORD

### Caveats 
- The snapshot command does not retain overridden environment variables since they can change during intermediate commands executed against a running envrironment. 
- The suite will not function on Windows. The incompatibilities at the moment lie in the `provision` command, since the executed command is Bash-compatible. Windows also requires additional configuration to run Linux-based containers. If Windows demand is present, it is possible to support all platforms in the future. 

-----

## Project Structure 
The suite is built around Docker Compose files and heavily utilizes Docker's ability to [extend Compose files](https://docs.docker.com/compose/extends/#multiple-compose-files).

The Starburst Presto service is defined in a Compose file at the project root. All other services will look up in the directory tree in order to reference the parent Presto service. Therefore, it is required that we provide the fully-qualified path relative to the project root when defining Docker resources. For example, suppose you have the following directory structure:

```
lib
├── .env
├── Dockerfile
├── docker-compose.yml
├── modules
│   ├── catalog
│   │   └── elasticsearch
│   │       ├── Dockerfile
│   │       ├── bootstrap.sh
│   │       ├── elasticsearch.yml
│   │       ├── presto
│   │       │   └── elasticsearch.properties
│   │       └── readme.md
│   ├── resources
│   └── security
└── snapshots
```

The `elasticsearch.yml` file looks like:

```yaml
version: "3.7"
services:

  presto:
    volumes:
      - "./modules/catalog/elasticsearch/presto/elasticsearch.properties:/usr/lib/presto/etc/catalog/elasticsearch.properties:ro"
  
  elasticsearch:
    build: 
      context: "./modules/catalog/elasticsearch/"
      args:
        - ELASTICSEARCH_VER=${ELASTICSEARCH_VER}
    image: "minipresto:elasticsearch"
    container_name: elasticsearch
    labels: 
      - "com.starburst.tests=minipresto"
      - "com.starburst.tests.module.elasticsearch=catalog-elasticsearch"
    ports:
      - 9200:9200
      - 9300:9300
```

Notice that the build context for the Dockerfile and the volume we mount to the Starburst Presto service are not relative to the `elasticsearch/` directory––it is relative to the parent directory which houses the top-level `docker-compose.yml` file. Also notice the label––this label will be used to identify resources related to testing suite so that the client commands actually work.

### Presto Dockerfile
The Presto CLI was removed in some Starburst Docker images starting sometime around late 323-e and 332-e. Instead of pulling a vanilla Starburst image, we toss in some extra configuration sugar by basing an image build off of a Starburst image, downloading the version's Presto CLI JAR file, and adding a Bash alias command. This ensures that one can invoke `presto` from inside the Presto container, and it will bring up the Presto CLI. This has been verified as compatible as far back as early 312-e images.

Additionally, the Dockerfile gives the `presto` user root privileges for commands that require sudo in bootstrap scripts.

-----

## Adding New Modules (Tutorial)
Adding new modules is relatively simple, but there are a few important guidelines to follow to ensure compatibility with the `minipresto` CLI. The design rules are the same for both catalogs and security modules. The best way to demonstrate this process is through a tutorial, so let's add a new catalog module for Postgres.

### Create the Relevant Directory
Since we are creating a new catalog, we will create a directory in the `modules/catalog/` directory.

```sh
mkdir lib/modules/catalog/postgres/
cd lib/modules/catalog/postgres/
```

### Add Presto Resources 
We want to place Presto-specific resources into a `presto/` directory. We will be mounting these resources to the Presto service defined in the root `docker-compose.yml` file. 

```sh
mkdir presto
```

In the newly-created `presto/` directory, let's add a properties file.

```sh
bash -c "cat << EOF > postgres.properties
connector.name=postgresql
connection-url=jdbc:postgresql://postgres:5432/minipresto
connection-user=admin
connection-password=password
EOF"
```

Notice the `postgres` in the connection URL: we are going to name our Docker service `postgres`, and Docker container networking will handle the rest for us (i.e. we don't need to worry about any IP addresses).

### Add the Docker Compose YAML
Now, in `lib/modules/catalog/postgres/`, let's add a Docker Compose file:

```sh
touch postgres.yml
```

Notice the naming convention––`postgres.yml`. Giving the same root name to both the parent directory `postgres/` and to the Docker Compose file `postgres.yml` will allow the `minipresto` CLI to find our new catalog module when we provision it. 

Let's add an environment file for the Postgres service in the `modules/catalog/postgres/` directory:

```sh
bash -c "cat << EOF > postgres.env
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
POSTGRES_DB=minipresto
EOF"
```

This file will initialize Postgres with a database `minipresto`, a user `presto`, and a password `password`.

### Review Progress 
Our directory tree should currently look like this (from the `/modules/catalog/` directory):

```
postgres
├── postgres.env
├── postgres.yml
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
    # You can make the volume read-only with `:ro` so that the container cannot write files to the host
    # Always place Presto files in `/usr/lib/presto/etc/` as symbolic links can change between versions
      - "./modules/catalog/postgres/presto/postgres.properties:/usr/lib/presto/etc/catalog/postgres.properties:ro"

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

- The standard `minipresto` resource label: `com.starburst.tests=minipresto`
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
      - "./modules/catalog/postgres/presto/postgres.properties:/usr/lib/presto/etc/catalog/postgres.properties:ro"

  postgres:
    image: "postgres:${POSTGRES_VER}"
    container_name: "postgres"
    labels: # These labels are applied to the service/container
      - "com.starburst.tests=minipresto"
      - "com.starburst.tests.module.postgres=catalog-postgres"
    env_file:
      - "./modules/catalog/postgres/postgres.env"
    volumes:
      - "postgres-data:/var/lib/postgresql/data"

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
We are all finished up. We can test our new catalog through the `minipresto` CLI:

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
If you need to customize an image for a specific use, you can do so via Dockerfiles. For example, the Elasticsearch catalog uses this approach to properly execute a bootstrap script at startup. 

### Bootstrap Scripts
Minipresto supports container bootstrap scripts. These scripts **do not replace** the entrypoint (or default command) for a given container. The script is copied from the Minipresto library to the container, executed, and then removed from the container. Containers are restarted after each bootstrap script execution, **so bootstrap scripts should not restart the container service**.

To add a bootstrap script, simply add a `resources/` directory in any given module, create a shell script, and then reference the script name in the Compose YAML file:

```yaml
version: "3.7"
services:

  presto:
    environment:
      MINIPRESTO_BOOTSTRAP: "bootstrap.sh"
```

### Managing Presto's `config.properties` File
Since numerous modules can change the `config.properties` file, it is highly recommended to not mount a `config.properties` file to the Presto container, but instead to modify the file the supported bootstrap script functionality. An example bootstrap snippet can be found below:

```bash
#!/usr/bin/env bash

set -euxo pipefail

echo "Adding Presto configs..."
cat <<EOT >> /usr/lib/presto/etc/config.properties
query.max-stage-count=105
query.max-execution-time=1h
query.max-execution-time=1h
EOT
```

Every time the `provision` command is executed, Minipresto will check for duplicate properties in `config.properties` and remove them if necessary.

-----

## Developer Notes
This section is limited and will be added to in the future. In general, it will cover:

- Major functions of the CLI
- Docker modules
- Project/library structure 
- Style guide
- Tests 

### Style Guide
- Python code is formatted with the Black formatting tool. Click command and option decorator functions do not have Black formatting applied to them because it looks incredibly obnoxious.
- All handled CLI errors should result in a `sys.exit(1)` to standardize the failed exit status. 
- All variables referencing directories should end with `_dir`.
- All variables referencing files should end with `_file`.
- Filesystem paths should be constructed with `os.path` when possible. 

### Tests
The tests are currently built to be compatible on MacOS. The tie to the operating system lies within the Docker daemon start/stop functions in the tests `helpers.py` file; these could be easily ported over to different Linux distributions. 

All tests can be chained together and automated with the exception of `test_config.py`. This is because all of the test cases require user input in the form of yes/no (easy to automate) and exiting `vi` (harder to automate).

Tests are built following the [Click testing guide](https://click.palletsprojects.com/en/7.x/testing/). 
