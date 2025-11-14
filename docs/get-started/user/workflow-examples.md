# Workflow Examples

This guide lists all of Minitrino's modules as well as some of the workflows
that the tool is best suited for.

## Overview

- [Workflow Examples](#workflow-examples)
  - [Overview](#overview)
  - [Module Documentation](#module-documentation)
    - [Enterprise vs Open Source Modules](#enterprise-vs-open-source-modules)
    - [Administration Modules](#administration-modules)
    - [Catalog Modules](#catalog-modules)
    - [Security Modules](#security-modules)
  - [CLI Examples](#cli-examples)
    - [Choosing a Trino or Starburst Version](#choosing-a-trino-or-starburst-version)
    - [Run Commands in Verbose Mode](#run-commands-in-verbose-mode)
    - [List Modules](#list-modules)
    - [Provision an Environment](#provision-an-environment)
    - [Access the UI](#access-the-ui)
    - [Worker Provisioning Overview](#worker-provisioning-overview)
    - [Modify Files in a Running Container](#modify-files-in-a-running-container)
    - [Access the Trino CLI](#access-the-trino-cli)
    - [Restart Cluster Containers](#restart-cluster-containers)
    - [View Cluster Resources](#view-cluster-resources)
    - [Shut Down an Environment](#shut-down-an-environment)
    - [Remove Minitrino Resources](#remove-minitrino-resources)
    - [Snapshot a Customized Module](#snapshot-a-customized-module)
    - [Point to a Starburst License File for Enterprise Modules](#point-to-a-starburst-license-file-for-enterprise-modules)
  - [Modify the Trino `config.properties` and `jvm.config` Files](#modify-the-trino-configproperties-and-jvmconfig-files)
    - [Method One: Docker Compose Environment Variables](#method-one-docker-compose-environment-variables)
    - [Method Two: Environment Variables](#method-two-environment-variables)
    - [Method Three: Bootstrap Scripts](#method-three-bootstrap-scripts)
  - [Bootstrap Scripts](#bootstrap-scripts)
    - [How Bootstrap Scripts Work](#how-bootstrap-scripts-work)
    - [Execution Context](#execution-context)
    - [Available Environment Variables](#available-environment-variables)
    - [Available Tools and Utilities](#available-tools-and-utilities)
    - [Creating a Bootstrap Script](#creating-a-bootstrap-script)
    - [Bootstrap Script Best Practices](#bootstrap-script-best-practices)
      - [Idempotency](#idempotency)
      - [Error Handling](#error-handling)
      - [External Service Dependencies](#external-service-dependencies)
      - [File Ownership](#file-ownership)
      - [Using Python in Bootstraps](#using-python-in-bootstraps)
    - [Debugging Bootstrap Scripts](#debugging-bootstrap-scripts)
      - [View Bootstrap Logs](#view-bootstrap-logs)
      - [Manually Execute Bootstrap](#manually-execute-bootstrap)
      - [Force Re-execution](#force-re-execution)
      - [Check Bootstrap Files](#check-bootstrap-files)
    - [Real-World Examples](#real-world-examples)
      - [Example 1: TLS Certificate Generation](#example-1-tls-certificate-generation)
      - [Example 2: Data Loading](#example-2-data-loading)
      - [Example 3: Configuration File Modification](#example-3-configuration-file-modification)
    - [Testing Bootstrap Scripts Locally](#testing-bootstrap-scripts-locally)
    - [When Bootstrap Scripts Fail](#when-bootstrap-scripts-fail)
    - [More Examples](#more-examples)

## Module Documentation

Each module has a `readme` associated with it. The list below points to the
`readme` files for each module.

### Enterprise vs Open Source Modules

Minitrino supports both Trino (open-source) and Starburst Enterprise modules.
The table below shows which modules require a Starburst license.

:::{tip} **Quick Reference:** ⭐ = Requires Starburst Enterprise license and
`IMAGE=starburst` :::

| Module Type  | Module Name              | License       | Description                                          |
| ------------ | ------------------------ | ------------- | ---------------------------------------------------- |
| **Admin**    | cache-service            | ⭐ Enterprise | Materialized view caching and table scan redirection |
| **Admin**    | data-products            | ⭐ Enterprise | Data products management and governance              |
| **Admin**    | file-group-provider      | OSS           | File-based group provider for authorization          |
| **Admin**    | insights                 | ⭐ Enterprise | Starburst Insights analytics and monitoring UI       |
| **Admin**    | ldap-group-provider      | ⭐ Enterprise | LDAP-based group integration                         |
| **Admin**    | minio                    | OSS           | S3-compatible object storage (MinIO)                 |
| **Admin**    | mysql-event-listener     | OSS           | MySQL-based audit logging and event tracking         |
| **Admin**    | resource-groups          | OSS           | Resource management and query queueing               |
| **Admin**    | results-cache            | ⭐ Enterprise | Query result caching for improved performance        |
| **Admin**    | scim                     | ⭐ Enterprise | SCIM 2.0 user and group synchronization              |
| **Admin**    | session-property-manager | OSS           | Manage session properties and defaults               |
| **Admin**    | spooling-protocol        | OSS           | Client-side result spooling protocol                 |
| **Admin**    | starburst-gateway        | ⭐ Enterprise | Starburst Gateway for query federation               |
| **Catalog**  | clickhouse               | OSS           | ClickHouse database connector                        |
| **Catalog**  | db2                      | ⭐ Enterprise | IBM Db2 database connector                           |
| **Catalog**  | delta-lake               | OSS           | Delta Lake table format support                      |
| **Catalog**  | elasticsearch            | OSS           | Elasticsearch search engine connector                |
| **Catalog**  | faker                    | OSS           | Faker data generator for testing                     |
| **Catalog**  | hive                     | OSS           | Hive Metastore with MinIO storage                    |
| **Catalog**  | iceberg                  | OSS           | Apache Iceberg REST catalog                          |
| **Catalog**  | iceberg-hms              | ⭐ Enterprise | Iceberg with Hive Metastore catalog                  |
| **Catalog**  | mariadb                  | OSS           | MariaDB database connector                           |
| **Catalog**  | mysql                    | OSS           | MySQL database connector                             |
| **Catalog**  | pinot                    | OSS           | Apache Pinot real-time analytics connector           |
| **Catalog**  | postgres                 | OSS           | PostgreSQL database connector                        |
| **Catalog**  | sqlserver                | OSS           | Microsoft SQL Server connector                       |
| **Catalog**  | stargate                 | ⭐ Enterprise | Stargate data federation connector                   |
| **Catalog**  | stargate-parallel        | ⭐ Enterprise | Stargate with parallel query execution               |
| **Security** | biac                     | ⭐ Enterprise | Built-in access control (BIAC)                       |
| **Security** | file-access-control      | OSS           | File-based authorization rules                       |
| **Security** | kerberos                 | OSS           | Kerberos authentication integration                  |
| **Security** | ldap                     | OSS           | LDAP authentication                                  |
| **Security** | oauth2                   | OSS           | OAuth 2.0 authentication                             |
| **Security** | password-file            | OSS           | Password file-based authentication                   |
| **Security** | tls                      | OSS           | TLS/SSL encryption for secure connections            |

**Using Enterprise Modules:**

Enterprise modules require:

1. Starburst Enterprise distribution: `IMAGE=starburst`
1. Valid Starburst license file (see
   [license configuration](#point-to-a-starburst-license-file-for-enterprise-modules))

```sh
# Example: Provision with enterprise module
minitrino -e IMAGE=starburst -e LIC_PATH=~/starburstdata.license provision -m insights
```

### Administration Modules

- [`cache-service`](../../modules/admin/cache-service)
- [`data-products`](../../modules/admin/data-products)
- [`file-group-provider`](../../modules/admin/file-group-provider)
- [`insights`](../../modules/admin/insights)
- [`ldap-group-provider`](../../modules/admin/ldap-group-provider)
- [`minio`](../../modules/admin/minio)
- [`mysql-event-listener`](../../modules/admin/mysql-event-listener)
- [`resource-groups`](../../modules/admin/resource-groups)
- [`results-cache`](../../modules/admin/results-cache)
- [`scim`](../../modules/admin/scim)
- [`session-property-manager`](../../modules/admin/session-property-manager)
- [`spooling-protocol`](../../modules/admin/spooling-protocol)
- [`starburst-gateway`](../../modules/admin/starburst-gateway)

### Catalog Modules

- [`clickhouse`](../../modules/catalog/clickhouse)
- [`db2`](../../modules/catalog/db2)
- [`delta-lake`](../../modules/catalog/delta-lake)
- [`elasticsearch`](../../modules/catalog/elasticsearch)
- [`faker`](../../modules/catalog/faker)
- [`hive`](../../modules/catalog/hive)
- [`iceberg`](../../modules/catalog/iceberg)
- [`iceberg-hms`](../../modules/catalog/iceberg-hms)
- [`mariadb`](../../modules/catalog/mariadb)
- [`mysql`](../../modules/catalog/mysql)
- [`pinot`](../../modules/catalog/pinot)
- [`postgres`](../../modules/catalog/postgres)
- [`sqlserver`](../../modules/catalog/sqlserver)
- [`stargate`](../../modules/catalog/stargate)
- [`stargate-parallel`](../../modules/catalog/stargate-parallel)

### Security Modules

- [`biac`](../../modules/security/biac)
- [`file-access-control`](../../modules/security/file-access-control)
- [`kerberos`](../../modules/security/kerberos)
- [`ldap`](../../modules/security/ldap)
- [`oauth2`](../../modules/security/oauth2)
- [`password-file`](../../modules/security/password-file)
- [`tls`](../../modules/security/tls)

## CLI Examples

### Choosing a Trino or Starburst Version

Each Minitrino release uses a default Trino version, specified in
`lib/minitrino.env` via the `CLUSTER_VER` variable. Unless overridden by an
environment variable, this is the version that will be used for all `provision`
commands.

To use Starburst instead of Trino, set the `IMAGE` environment variable to
`starburst`. Starburst Enterprise (SEP) releases are based on Trino releases.
So, SEP release `400-e` directly maps to Trino release `400`. To clearly
demonstrate the relationship, here are few more examples:

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

When a certain `CLUSTER_VER` is deployed for the first time, Minitrino must
first build the image. This typically takes ~ 5 minutes depending on the quality
of your network. Once a given `CLUSTER_VER` is built, it will be reused for all
future commands specifying the same version.

Provision a single-node cluster using the default Trino version:

```sh
minitrino -v provision
```

Provision a multi-node cluster with two worker nodes:

```sh
minitrino -v provision --workers 2
```

Provision the `postgres` catalog module with a specific Trino version:

```sh
minitrino -v -e CLUSTER_VER=${VER} provision -m postgres
```

Provision with Starburst instead of Trino:

```sh
minitrino -v -e IMAGE=starburst -e CLUSTER_VER=476-e provision -m postgres
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

The coordinator container can be directly accessed via:

```sh
docker exec -it minitrino-default bash
```

**Note**: The default cluster name is `default`. If you provisioned with a
custom cluster name (e.g., `--cluster my-cluster`), replace `minitrino-default`
with `minitrino-my-cluster`.

### Worker Provisioning Overview

When you provision an environment with one or more workers, the following events
take place:

- The coordinator container is deployed and any relevant bootstrap scripts are
  executed inside of it.
- The coordinator is restarted.
- Once the coordinator is up, the worker containers are deployed, and the
  coordinator's `/mnt/etc/` directory is compressed, copied, and extracted to
  all of the worker containers.
- The workers' `config.properties` files are overwritten with basic
  configurations for connectivity to the coordinator.

This ensures that any distributed files, such as catalog files, are placed on
every container in the cluster. It also ensures that coordinator-specific
configurations do not remain on the workers.

### Modify Files in a Running Container

You can modify files inside a running container. For example:

```sh
# Update coordinator logging settings
docker exec -it minitrino-default bash
echo "io.trino=DEBUG" >> /mnt/etc/log.properties
exit
docker restart minitrino-default

# Update worker logging settings (assuming default cluster name)
docker exec -it minitrino-worker-1-default bash
echo "io.trino=DEBUG" >> /mnt/etc/log.properties
exit
docker restart minitrino-worker-1-default
```

Restarting the container allows Trino to register the configuration change.

**Note**: Replace `default` with your cluster name if using a custom cluster.

### Access the Trino CLI

```sh
docker exec -it minitrino-default bash
trino-cli --debug --user admin --execute "SELECT * FROM tpch.tiny.customer LIMIT 10"
```

### Restart Cluster Containers

Restart all containers in the cluster without reprovisioning:

```sh
minitrino restart
```

This is useful when you've made configuration changes and need to reload the
cluster without tearing it down completely.

### View Cluster Resources

View all resources associated with your cluster:

```sh
minitrino resources
```

Filter by specific resource types:

```sh
# View only containers
minitrino resources --container

# View only volumes
minitrino resources --volume

# View only images
minitrino resources --image

# View only networks
minitrino resources --network
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

Remove all Minitrino-labeled images (requires `--cluster all` or `-c all`):

```sh
minitrino -c all remove --images
```

Remove images from a specific module:

```sh
minitrino remove --images \
  --label org.minitrino.module.${MODULE_TYPE}.${MODULE}=true
```

Where `${MODULE_TYPE}` is one of: `admin`, `catalog`, `security`.

Remove all Minitrino-labeled volumes:

```sh
minitrino remove --volumes
```

Remove volumes from a specific module:

```sh
minitrino remove --volumes \
  --label org.minitrino.module.${MODULE_TYPE}.${MODULE}=true
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

:::{note} **Which modules require a license?** See the
[Enterprise Module Reference](#enterprise-vs-open-source-modules) table above
for a complete list of enterprise vs open-source modules. :::

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

More information about environment variables
[can be found here](environment-variables-and-config).

## Modify the Trino `config.properties` and `jvm.config` Files

Many modules may change the Trino's `config.properties` and `jvm.config` files.
There are two supported ways to modify these files.

### Method One: Docker Compose Environment Variables

Minitrino has special support for two Trino-specific environment variables:
`CONFIG_PROPERTIES` and `JVM_CONFIG`. Below is an example of setting these
variables in a Docker Compose file:

```yaml
minitrino:
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

Bootstrap scripts allow you to customize container initialization with arbitrary
shell commands. These scripts execute at specific lifecycle stages and can
modify configurations, load data, or initialize external services.

### How Bootstrap Scripts Work

1. **Minitrino copies** bootstrap scripts from the library to the container
1. **Scripts execute** in two phases: `before_start` and `after_start`
1. **Container restarts** after each bootstrap execution
1. **Idempotency checks:** Minitrino checksums scripts and only re-executes if
   content changes

**Important:** Bootstrap scripts do NOT replace the container's entrypoint. They
augment the startup process.

### Execution Context

**User and Permissions:**

- Scripts initially run as **root**
- After execution, ownership of `/etc/${CLUSTER_DIST}` changes to service user
  (trino/starburst)
- Scripts can use `sudo` for privileged operations
- Files created should be owned by `${SERVICE_USER}` for persistence

**Execution Phases:**

1. **`before_start()`**:
   - Runs before Trino/Starburst server starts
   - Use for: config generation, certificate setup, schema initialization
   - Trino/Starburst service is NOT available yet

1. **`after_start()`**:
   - Runs after Trino/Starburst is accepting queries
   - Use for: data loading, SQL execution, post-startup validation
   - Trino/Starburst service IS available (can use `trino-cli`)

### Available Environment Variables

Your bootstrap script has access to these key variables:

```bash
$CLUSTER_DIST         # "trino" or "starburst"
$CLUSTER_VER          # Version number (e.g., "476")
$CLUSTER_NAME         # Cluster name (e.g., "default")
$SERVICE_USER         # Service user ("trino" or "starburst")
$HOSTNAME             # Container hostname
$COORDINATOR          # "true" for coordinator, "false" for workers
```

All Docker Compose environment variables are also available.

### Available Tools and Utilities

Bootstrap scripts have access to a rich toolset:

- **Networking:** `curl`, `wget`, `ping`, `telnet`
- **Data:** `jq` (JSON processor)
- **Trino:** `trino-cli` (for SQL execution in `after_start`)
- **Security:** `keytool` (Java keystore), `openssl`, `ldap-utils`, `krb5-user`
- **Utilities:** `wait-for-it` (wait for services), `vim`, `tree`, `less`
- **Python:** Python 3 with pip (can install additional packages)

### Creating a Bootstrap Script

**1. Create the script directory:**

```sh
mkdir -p lib/modules/${type}/${module}/resources/bootstrap/
```

**2. Write the script:**

```bash
#!/usr/bin/env bash

set -euxo pipefail

before_start() {
    echo "Executing before Trino starts..."

    # Example: Modify config file
    echo "discovery.uri=http://custom-coordinator:8080" >> /etc/${CLUSTER_DIST}/config.properties

    # Example: Wait for external service
    wait-for-it postgres:5432 --strict --timeout=30

    # Example: Generate certificates (as root)
    keytool -genkeypair -alias mykey ...

    # Example: Fix ownership
    chown -R ${SERVICE_USER}:root /etc/${CLUSTER_DIST}/custom/
}

after_start() {
    echo "Executing after Trino started..."

    # Example: Load data via SQL
    trino-cli --user admin --execute "CREATE SCHEMA IF NOT EXISTS hive.default"

    # Example: Validate setup
    if trino-cli --user admin --execute "SELECT 1"; then
        echo "Cluster is ready!"
    else
        echo "Cluster validation failed!"
        exit 1
    fi
}
```

**3. Reference in Docker Compose YAML:**

```yaml
services:
  minitrino:
    environment:
      MINITRINO_BOOTSTRAP: bootstrap.sh
```

**4. Test the module:**

```sh
minitrino -v provision -m ${module}
```

### Bootstrap Script Best Practices

#### Idempotency

Always check if operations were already completed:

```bash
before_start() {
    # Check if index already exists
    if curl -s http://elasticsearch:9200/_cat/indices | grep -q 'myindex'; then
        echo "Index already exists, skipping creation"
        return 0
    fi

    # Create index
    curl -XPUT http://elasticsearch:9200/myindex ...
}
```

#### Error Handling

Use `set -e` to exit on errors, but handle expected failures:

```bash
set -euxo pipefail  # Exit on error, undefined vars, pipe failures

before_start() {
    # This will exit script if command fails
    keytool -genkeypair ...

    # Handle expected failures
    if ! some_optional_command; then
        echo "Optional command failed, continuing..."
    fi
}
```

#### External Service Dependencies

Wait for services to be ready:

```bash
before_start() {
    # Wait for service to be available
    wait-for-it elasticsearch:9200 --strict --timeout=60 -- \
        echo "Elasticsearch is up"

    # Alternative: manual retry logic
    retries=30
    until curl -s http://postgres:5432 > /dev/null 2>&1; do
        retries=$((retries - 1))
        if [ $retries -eq 0 ]; then
            echo "Postgres failed to start"
            exit 1
        fi
        sleep 1
    done
}
```

#### File Ownership

Ensure files are owned by the service user:

```bash
before_start() {
    # Create files as root
    echo "config-value" > /etc/${CLUSTER_DIST}/custom.properties

    # Fix ownership for service user
    chown ${SERVICE_USER}:root /etc/${CLUSTER_DIST}/custom.properties
    chmod 644 /etc/${CLUSTER_DIST}/custom.properties
}
```

#### Using Python in Bootstraps

Install packages and run Python scripts:

```bash
before_start() {
    # Install Python packages
    sudo pip install requests faker

    # Run inline Python
    python3 << 'EOF'
import requests
response = requests.get('http://service:8080/health')
print(f"Health check: {response.status_code}")
EOF

    # Or execute external script
    python3 /mnt/bootstrap/mymodule/myscript.py
}
```

### Debugging Bootstrap Scripts

#### View Bootstrap Logs

```sh
# Check if bootstraps completed
docker logs minitrino-default 2>&1 | grep BOOTSTRAP

# View bootstrap script execution
docker logs minitrino-default 2>&1 | grep -A 50 "before_start"
```

#### Manually Execute Bootstrap

```sh
# Enter container
docker exec -it minitrino-default bash

# View bootstrap script
cat /tmp/minitrino/bootstrap/mymodule/bootstrap.sh

# Execute manually
bash -x /tmp/minitrino/bootstrap/mymodule/bootstrap.sh
```

#### Force Re-execution

Minitrino tracks bootstrap checksums to avoid re-running unchanged scripts:

```sh
# Remove checksum file to force re-execution
docker exec minitrino-default rm /etc/trino/.minitrino/bootstrap_checksums.json

# Restart container (will re-run bootstraps)
docker restart minitrino-default
```

#### Check Bootstrap Files

```sh
# View bootstrap directory structure
docker exec minitrino-default tree /tmp/minitrino/bootstrap/

# Check what's mounted
docker exec minitrino-default ls -la /mnt/bootstrap/
```

### Real-World Examples

#### Example 1: TLS Certificate Generation

From `security/tls/resources/cluster/bootstrap.sh`:

```bash
before_start() {
    local ssl_dir=/mnt/etc/tls

    # Check if certificates exist
    if [[ -f "${ssl_dir}/keystore.jks" ]]; then
        echo "TLS artifacts already exist, skipping generation"
        return 0
    fi

    # Generate keystore
    keytool -genkeypair \
        -alias minitrino \
        -keyalg RSA \
        -keystore "${ssl_dir}/keystore.jks" \
        -storepass changeit \
        -validity 3650 \
        -dname "CN=*.minitrino.com"

    # Export certificate
    keytool -export \
        -alias minitrino \
        -keystore "${ssl_dir}/keystore.jks" \
        -file "${ssl_dir}/minitrino_cert.cer" \
        -storepass changeit
}
```

#### Example 2: Data Loading

From `catalog/elasticsearch/resources/cluster/bootstrap-es.sh`:

```bash
before_start() {
    # Wait for Elasticsearch
    wait-for-it elasticsearch:9200 --strict --timeout=60

    # Check if index exists
    if curl -s http://elasticsearch:9200/_cat/indices | grep -q 'user'; then
        echo "Index already exists, skipping"
        return 0
    fi

    # Create index
    curl -XPUT http://elasticsearch:9200/user -H 'Content-Type: application/json' -d '{
        "settings": { "number_of_replicas": 0 }
    }'

    # Install Python dependencies
    sudo pip install faker requests

    # Generate and load data
    python3 << 'EOF'
import requests
from faker import Faker
fake = Faker()
for i in range(1, 500):
    user = {"name": fake.name(), "email": fake.email()}
    requests.post("http://elasticsearch:9200/user/_doc/" + str(i), json=user)
EOF
}
```

#### Example 3: Configuration File Modification

```bash
before_start() {
    # Append to JVM config
    echo "-Djava.security.krb5.conf=/etc/krb5.conf" >> /etc/${CLUSTER_DIST}/jvm.config

    # Modify config.properties
    cat << EOF >> /etc/${CLUSTER_DIST}/config.properties
http-server.authentication.krb5.service-name=trino
http-server.authentication.krb5.keytab=/etc/trino.keytab
EOF

    # Ensure ownership
    chown -R ${SERVICE_USER}:root /etc/${CLUSTER_DIST}/
}
```

### Testing Bootstrap Scripts Locally

Before adding to a module, test bootstrap logic locally:

```sh
# 1. Provision cluster without custom bootstrap
minitrino -v provision -m base-module

# 2. Copy test script into container
docker cp my-bootstrap.sh minitrino-default:/tmp/test-bootstrap.sh

# 3. Execute manually
docker exec -it minitrino-default bash -x /tmp/test-bootstrap.sh

# 4. Verify results
docker exec -it minitrino-default cat /etc/trino/config.properties
```

### When Bootstrap Scripts Fail

If provisioning hangs or fails during bootstrap:

1. **Check logs:** `docker logs minitrino-default 2>&1 | tail -100`
1. **Look for errors:** Search for "ERROR", "failed", or stack traces
1. **Verify external services:** Ensure dependencies (DBs, etc.) are running
1. **Test interactively:** Enter container and run script manually
1. **Simplify script:** Comment out sections to isolate the failure
1. **Check permissions:** Verify files/directories are accessible

After fixing issues, destroy and re-provision:

```sh
minitrino down
minitrino remove --volumes
minitrino -v provision -m ${module}
```

### More Examples

Additional bootstrap examples can be found in the library:

- **TLS setup:** `lib/modules/security/tls/resources/cluster/bootstrap.sh`
- **LDAP configuration:**
  `lib/modules/security/ldap/resources/cluster/bootstrap.sh`
- **OAuth2 setup:** `lib/modules/security/oauth2/resources/cluster/bootstrap.sh`
- **BIAC initialization:**
  `lib/modules/security/biac/resources/cluster/bootstrap.sh`
- **Elasticsearch data loading:**
  `lib/modules/catalog/elasticsearch/resources/cluster/bootstrap-es.sh`
