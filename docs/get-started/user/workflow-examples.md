# Workflow Examples

This guide lists all of Minitrino's modules as well as some of the workflows
that the tool is best suited for.

## Overview

- [Workflow Examples](#workflow-examples)
  - [Overview](#overview)
  - [Module Documentation](#module-documentation)
    - [Administration Modules](#administration-modules)
    - [Catalog Modules](#catalog-modules)
    - [Security Modules](#security-modules)
  - [CLI Examples](#cli-examples)
    - [Choosing a Starburst Version](#choosing-a-starburst-version)
    - [Run Commands in Verbose Mode](#run-commands-in-verbose-mode)
    - [List Modules](#list-modules)
    - [Provision an Environment](#provision-an-environment)
    - [Access the UI](#access-the-ui)
    - [Worker Provisioning Overview](#worker-provisioning-overview)
    - [Modify Files in a Running Container](#modify-files-in-a-running-container)
    - [Access the Trino CLI](#access-the-trino-cli)
    - [Shut Down an Environment](#shut-down-an-environment)
    - [Remove Minitrino Resources](#remove-minitrino-resources)
    - [Snapshot a Customized Module](#snapshot-a-customized-module)
    - [Point to a Starburst License File for Enterprise Modules](#point-to-a-starburst-license-file-for-enterprise-modules)
  - [Modify the Trino `config.properties` and `jvm.config` Files](#modify-the-trino-configproperties-and-jvmconfig-files)
    - [Method One: Docker Compose Environment Variables](#method-one-docker-compose-environment-variables)
    - [Method Two: Environment Variables](#method-two-environment-variables)
    - [Method Three: Bootstrap Scripts](#method-three-bootstrap-scripts)
  - [Bootstrap Scripts](#bootstrap-scripts)

## Module Documentation

Each module has a `readme` associated with it. The list below points to the
`readme` files for each module.

### Administration Modules

- [`cache-service`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/admin/cache-service/readme.md)
- [`data-products`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/admin/data-products/readme.md)
- [`file-group-provider`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/admin/file-group-provider/readme.md)
- [`insights`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/admin/insights/readme.md)
- [`mysql-event-listener`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/admin/mysql-event-listener/readme.md)
- [`resource-groups`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/admin/resource-groups/readme.md)
- [`results-cache`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/admin/results-cache/readme.md)
- [`session-property-manager`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/admin/session-property-manager/readme.md)

### Catalog Modules

- [`clickhouse`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/clickhouse/readme.md)
- [`db2`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/db2/readme.md)
- [`delta-lake`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/delta-lake/readme.md)
- [`elasticsearch`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/elasticsearch/readme.md)
- [`faker`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/faker/readme.md)
- [`hive`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/hive/readme.md)
- [`iceberg`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/iceberg/readme.md)
- [`mariadb`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/mariadb/readme.md)
- [`mysql`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/mysql/readme.md)
- [`pinot`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/pinot/readme.md)
- [`postgres`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/postgres/readme.md)
- [`sqlserver`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/sqlserver/readme.md)

### Security Modules

- [`biac`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/security/biac/readme.md)
- [`file-access-control`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/security/file-access-control/readme.md)
- [`ldap`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/security/ldap/readme.md)
- [`oauth2`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/security/oauth2/readme.md)
- [`password-file`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/security/password-file/readme.md)
- [`tls`](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/security/tls/readme.md)

## CLI Examples

### Choosing a Starburst Version

Each Minitrino release uses a default Starburst version, specified in
`lib/minitrino.env` via the `STARBURST_VER` variable. Unless overridden by an
environment variable, this is the version that will be used for all `provision`
commands.

Starburst Enterprise (SEP) releases are based on Trino releases. So, SEP release
`400-e` directly maps to Trino release `400`. To clearly demonstrate the
relationship, here are few more examples:

- SEP `413-e.9` -> Trino `413`
- SEP `446-e` -> Trino `446`
- SEP `453-e.4` -> Trino `453`
- SEP `460-e` -> Trino `460`

Nearly all Trino plugins are exposed in SEP, so anything documented in the Trino
docs should be configurable in the related SEP image.

### Run Commands in Verbose Mode

It is recommended to run the majority of Minitrino commands in verbose mode. To
do so, simply add the `-v` option to any command:

```sh
minitrino -v ...
```

### List Modules

To see which modules exist (without needing to reference this wiki), make use of
the `modules` command.

List all modules:

```sh
minitrino modules
```

List all modules of a given type (one of `admin`, `catalog`, `security`):

```sh
minitrino modules --type admin 
minitrino modules --type catalog 
minitrino modules --type security 
```

The `--json` option can be used to dump all metadata tied to a module(s), such
as the module's directory, its Docker Compose file location, and a JSON
representation of the entire Docker Compose file.

Using `jq`, the command can be manipulated to show many different groupings of
information.

```sh
minitrino modules -m ldap --json

# Return the module directory
minitrino modules -m ${module} --json | jq .${module}.module_dir

# Return the module's Compose file location
minitrino modules -m ${module} --json | jq .${module}.yaml_dict
```

### Provision an Environment

When a certain `STARBURST_VER` is deployed for the first time, Minitrino must
first build the image. This typically takes ~ 5 minutes depending on the quality
of your network. Once a given `STARBURST_VER` is built, it will be reused for
all future commands specifying the same version.

Provision a single-node cluster using the default SEP version:

```sh
minitrino -v provision
```

Provision a multi-node cluster with two worker nodes:

```sh
minitrino -v provision --workers 2
```

Provision the `postgres` catalog module with a specific [SEP
version](https://docs.starburst.io/latest/release.html):

```sh
minitrino -v -e STARBURST_VER=${VER} provision -m postgres
```

Provision the `hive` catalog module with two worker nodes:

```sh
minitrino -v provision -m hive --workers 2
```

Append the running Hive environment with the `iceberg` module and downsize to
one worker (the `hive` module will be included automatically):

```sh
minitrino -v provision -m iceberg --workers 1
```

Provision Trino with password authentication, which will include the `tls`
module as a dependency and expose the service on `https://localhost:8443`:

```sh
minitrino -v provision -m password-file
```

Provision multiple password authenticators in tandem:

```sh
minitrino -v provision -m ldap -m password-file
```

### Access the UI

All environments expose the Starburst service on `localhost:8080`, meaning you
can visit the web UI directly, or you can connect external clients, such as
DBeaver, to the `localhost` service.

The `trino` coordinator container can be directly accessed via:

```sh
docker exec -it trino bash 
```

### Worker Provisioning Overview

When you provision an environment with one or more workers, the following events
take place:

- The coordinator container is deployed and any relevant bootstrap scripts are
  executed inside of it.
- The coordinator is restarted.
- Once the coordinator is up, the worker containers are deployed, and the
  coordinator's `/etc/starburst/` directory is compressed, copied, and extracted
  to all of the worker containers.
- The workers' `config.properties` files are overwritten with basic
  configurations for connectivity to the coordinator.

This ensures that any distributed files, such as catalog files, are placed on
every container in the cluster. It also ensures that coordinator-specific
configurations do not remain on the workers.

### Modify Files in a Running Container

You can modify files inside a running container. For example:

```sh
# Update coordinator logging settings
docker exec -it trino bash 
echo "io.trino=DEBUG" >> /etc/starburst/log.properties
exit
docker restart trino

# Update worker logging settings
docker exec -it trino-worker-1 bash 
echo "io.trino=DEBUG" >> /etc/starburst/log.properties
exit
docker restart trino-worker-1
```

Restarting the container allows Trino to register the configuration change.

### Access the Trino CLI

```sh
docker exec -it trino bash 
trino-cli --debug --user admin --execute "SELECT * FROM tpch.tiny.customer LIMIT 10"
```

### Shut Down an Environment

```sh
minitrino down
```

To skip graceful shutdown and stop all containers immediately, run:

```sh
minitrino down --sig-kill
```

The default behavior of the `down` command removes containers. To stop the
containers instead of removing them, run:

```sh
minitrino down --keep
```

### Remove Minitrino Resources

Minitrino creates volumes and pulls/builds various images to support each
module. All resources are labeled with project-specific metadata, so all
`remove` commands will target Docker resources specifically tied to Minitrino
modules.

Remove all Minitrino-labeled images:

```sh
minitrino remove --images
```

Remove images from a specific module:

```sh
minitrino remove --images \
  --label com.starburst.tests.module.${MODULE}=${MODULE_TYPE}-${MODULE}
```

Where `${MODULE_TYPE}` is one of: `admin`, `catalog`, `security`.

Remove all Minitrino-labeled volumes:

```sh
minitrino remove --volumes
```

Remove volumes from a specific module:

```sh
minitrino remove --volumes \
  --label com.starburst.tests.module.${MODULE}=${MODULE_TYPE}-${MODULE}
```

### Snapshot a Customized Module

Users designing and customizing their own modules can persist them for later
usage with the `snapshot` command. For example, if a user modifies the `hive`
module, they can persist their changes by running:

```sh
minitrino snapshot --name ${SNAPSHOT_NAME} -m hive
```

By default, the snapshot file is placed in
`${LIB_PATH}/${SNAPSHOT_NAME}.tar.gz`. The snapshot can be saved to a different
directory by passing the `--directory` option to the `snapshot` command.

### Point to a Starburst License File for Enterprise Modules

Pass an environment variable directly to the command:

```sh
minitrino -e LIC_PATH=/path/to/starburstdata.license provision -m insights
```

Export the environment variable to the shell:

```sh
export LIC_PATH=/path/to/starburstdata.license
minitrino provision -m insights
```

Add the variable to the `minitrino.cfg` file:

```sh
minitrino config

# Edit the config file
[config]
LIC_PATH=~/work/license/starburstdata.license

# Enterprise modules now automatically receive the license file
minitrino provision -m insights
```

More information about environment variables [can be found
here](https://github.com/jefflester/minitrino/wiki/Environment-Variables-and-Config).

## Modify the Trino `config.properties` and `jvm.config` Files

Many modules may change the Trino's `config.properties` and `jvm.config` files.
There are two supported ways to modify these files.

### Method One: Docker Compose Environment Variables

Minitrino has special support for two Trino-specific environment variables:
`CONFIG_PROPERTIES` and `JVM_CONFIG`. Below is an example of setting these
variables in a Docker Compose file:

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

### Method Two: Environment Variables

Environment variables can be exported prior to executing a `provision` command:

```sh
export CONFIG_PROPERTIES=$'query.max-stage-count=85\ndiscovery.uri=http://trino:8080'
export JVM_CONFIG=$'-Xmx2G\n-Xms1G'

minitrino -v provision
```

Note that multiple configs can be separated with a newline, though `$'...'`
syntax must be used, as it allows you to include escape sequences like `\n` that
are interpreted as actual newlines.

As an alternative to using `export` to set environment variables, they can also
be passed directly to the `provision` command:

```sh
minitrino -v \
  --env CONFIG_PROPERTIES=$'query.max-stage-count=85\ndiscovery.uri=http://trino:8080' \
  --env JVM_CONFIG=$'-Xmx2G\n-Xms1G' \
  provision
```

Single configs are simpler and do not require `$'...'` syntax:

```sh
minitrino -v \
  --env CONFIG_PROPERTIES='query.max-stage-count=85' \
  --env JVM_CONFIG='-Xmx2G' \
  provision
```

### Method Three: Bootstrap Scripts

The `config.properties` and `jvm.config` files can be modified directly with a
module [bootstrap script](#bootstrap-scripts).

## Bootstrap Scripts

Minitrino supports container bootstrap scripts. These scripts **do not replace**
the entrypoint (or default command) for a container. The script is copied from
the Minitrino library to the container, executed, and then removed from the
container. Containers are restarted after each bootstrap script execution.

If a bootstrap script has already executed in a container, Minitrino will not
re-execute the bootstrap script *unless the contents of the script have
changed*. The is useful after running `minitrino down --keep`––this way, the
subsequent `provision` command will not re-execute the same bootstrap script(s).

In general, if a bootstrap script is updated, it is recommended to destroy and
re-provision the Minitrino environment.

To add a bootstrap script, add a `resources/bootstrap/` directory in any given
module, create a shell script, and then reference the script name in the Compose
YAML file via the `MINITRINO_BOOTSTRAP` environment variable:

```yaml
services:

  trino:
    environment:
      MINITRINO_BOOTSTRAP: bootstrap.sh
```

See the `elasticsearch` module for an example of a module that uses a bootstrap
script.
