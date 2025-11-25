# Build a Module

The following example demonstrates the creation of a new catalog module for a
Postgres service.

## Overview

- [Build a Module](#build-a-module)
  - [Overview](#overview)
  - [Library Overview](#library-overview)
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

## Library Overview

Understanding the shape and functionality of the library will help conceptualize
how modules are built.

Minitrino's library is built around Docker Compose files and utilizes Docker's
ability to
[extend Compose files](https://docs.docker.com/compose/extends/#multiple-compose-files).
The `trino` container is defined in the `docker-compose.yaml` file at the
library root, and all nested module Compose files reference the root
`docker-compose.yaml` file.

The library structure:

```text
lib/
├── docker-compose.yaml
├── image
│   ├── Dockerfile
│   └── src
├── minitrino.env
├── modules
│   ├── admin
│   ├── catalog
│   ├── resources
│   └── security
├── snapshots
└── version
```

## Create the Module Directory

To start, create the module's directory in the `lib/modules/catalog/` directory:

```sh
mkdir lib/modules/catalog/my-postgres/
cd lib/modules/catalog/my-postgres/
```

## Add Trino Resources

All resources for a module go inside of the `resources/` directory within the
module's directory (`lib/modules/${type}/${module}/`). Inside this directory,
place Trino-specific resources into a `cluster/` directory, then mount the
resources to the Trino container defined in the root `docker-compose.yaml` file.

```sh
mkdir -p resources/cluster/
```

In the newly-created `resources/cluster/` directory, add a properties file.

```sh
bash -c "cat << EOF > resources/cluster/postgres.properties
connector.name=postgresql
connection-url=jdbc:postgresql://postgres:5432/minitrino
connection-user=admin
connection-password=trinoRocks15
EOF"
```

______________________________________________________________________

**Note**: Passwords in default modules tend to be `trinoRocks15`. For
consistency throughout the library, it is recommended to use this password.

______________________________________________________________________

## Add the Docker Compose YAML

In `lib/modules/catalog/my-postgres/`, add a Docker Compose file:

```sh
touch my-postgres.yaml
```

Note the naming convention: `my-postgres.yaml`. Giving the same root name of
"my-postgres" to both the parent directory `my-postgres/` and to the Docker
Compose file `my-postgres.yaml` will allow the CLI to find the new module's
Compose file.

Next, add an environment file for the Postgres container. Non-Trino resources
should go into their own directory, so create one for Postgres:

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

## Add a Metadata File

The `metadata.json` file exposes key information about the module. **It is
required for a module to work with the CLI.**

In `lib/modules/catalog/my-postgres/`, add a `metadata.json` file:

```sh
bash -c 'cat << EOF > metadata.json
{
  "description": "Example Postgres catalog module",
  "incompatibleModules": [],
  "dependentModules": [],
  "enterprise": false
}
EOF'
```

### Metadata Field Reference

#### Required Fields

- **`description`** (string, required): Human-readable description of the
  module's purpose and functionality.
  ```json
  "description": "PostgreSQL catalog connector with async query support"
  ```

#### Optional Fields

- **`enterprise`** (boolean, optional, default: `false`): Indicates whether the
  module requires a Starburst Enterprise license (`starburstdata.license`). Set
  to `true` for Starburst-exclusive features.

  ```json
  "enterprise": true
  ```

- **`incompatibleModules`** (array of strings, optional): Lists modules that
  cannot be provisioned alongside this module due to conflicts (e.g., port
  collisions, conflicting configurations). Use `["*"]` wildcard to indicate
  incompatibility with all other modules.

  ```json
  "incompatibleModules": ["ldap", "oauth2"]
  ```

- **`dependentModules`** (array of strings, optional): Specifies prerequisite
  modules that must be provisioned alongside this module. Minitrino will
  automatically include these during provisioning.

  ```json
  "dependentModules": ["minio", "hive"]
  ```

- **`versions`** (array of strings, optional): Defines version compatibility
  constraints for the module. Array can contain 0-2 items representing
  `[minVersion, maxVersion]`. Use `"9999"` to indicate no upper bound. Empty
  array `[]` means no version constraints.

  ```json
  "versions": ["466", "9999"]  // Works with Trino/Starburst 466 and above
  "versions": ["443", "465"]   // Works only with versions 443-465
  "versions": []               // No version constraints
  ```

- **`dependentClusters`** (array of objects, optional): **Advanced feature** for
  multi-cluster orchestration. Defines additional clusters that should be
  automatically provisioned alongside the primary cluster. Used by modules like
  `starburst-gateway` and `stargate` for federated query scenarios.

  Each object requires:

  - `name` (string): Unique name for the dependent cluster
  - `modules` (array of strings): Modules to provision in the dependent cluster
  - `workers` (number): Number of worker nodes (0 for coordinator-only)
  - `env` (object): Environment variables specific to this cluster

  ```json
  "dependentClusters": [
    {
      "name": "stargate-remote",
      "modules": ["hive", "password-file"],
      "workers": 0,
      "env": {
        "__PORT_MINITRINO": "60801",
        "CONFIG_PROPERTIES": "http-server.process-forwarded=true"
      }
    }
  ]
  ```

### Metadata Schema Validation

All metadata files are validated against a JSON schema during CLI operations. If
validation fails, Minitrino will provide detailed error messages indicating
which fields are invalid.

### Example: Complete Metadata File

```json
{
  "description": "Iceberg catalog with REST metadata management and S3 storage",
  "incompatibleModules": [],
  "dependentModules": ["minio"],
  "enterprise": false,
  "versions": ["443", "9999"],
  "dependentClusters": []
}
```

### Viewing Metadata

The metadata can be exposed via the `modules` command:

```sh
minitrino modules -m ${module}
```

## Add a Readme File

This step is not required for personal development, but it is required prior to
merging modules into the master branch.

In `lib/modules/catalog/my-postgres/`, add a `readme.md` file:

```sh
touch readme.md
```

This file should contain an overview of the module.

## Review Progress

The resulting directory tree should look like this (from the
`lib/modules/catalog/` directory):

```sh
my-postgres
├── metadata.json
├── my-postgres.yaml
├── readme.md
└── resources
    ├── cluster
    │   └── postgres.properties
    └── postgres
        └── postgres.env
```

## Configure the Docker Compose YAML File

We will now define the `my-postgres.yaml` Docker Compose file:

```yaml
services:
  minitrino:
    volumes:
      - ./modules/catalog/my-postgres/resources/cluster/postgres.properties:/mnt/etc/catalog/postgres.properties:ro

  postgres:
    image: postgres:${POSTGRES_VER}
    container_name: postgres-${CLUSTER_NAME}
    env_file:
      - ./modules/catalog/my-postgres/resources/postgres/postgres.env
    ports:
      - ${__PORT_POSTGRES}:5432
    volumes:
      - postgres-data:/var/lib/postgresql/data
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.my-postgres=true

volumes:
  postgres-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.my-postgres=true
```

## Important Implementation Details: Paths and Labels

### Path References for Volumes and Build Contexts

Volumes mounted in Docker Compose files _are not relative to the Compose file
itself_, they are relative to the base `docker-compose.yaml` file in the
library's root directory. This is because the CLI extends Compose files, meaning
that all path references in child Compose files need to be relative to the
positioning of the parent Compose file.

Additional information can be found about extending Compose files in the
[Docker docs](https://docs.docker.com/compose/extends/#multiple-compose-files).

### Minitrino Docker Labels

All Minitrino Docker Compose files use labels. The labels associate containers,
volumes, and images with Minitrino and allow the CLI to target those objects
when executing commands.

Applying labels to the `minitrino` container is only necessary when `minitrino`
is the only service defined in the Compose file. The
[`biac` module](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/security/biac/biac.yaml)
is an example of this.

Labels should always be applied to the following objects:

- Containers
- Named volumes
- Images built from a Dockerfile (similar to how it's defined in the
  [root `docker-compose.yaml` file](https://github.com/jefflester/minitrino/blob/master/src/lib/docker-compose.yaml))

Labels should be defined in pairs of two. The naming convention is:

- The standard Minitrino resource label: `org.minitrino.root=true`
- A module-specific resource label:
  `org.minitrino.module.${MODULE_TYPE}.${MODULE_NAME}=true`
  - Module type can be one of: `admin`, `catalog`, or `security`
  - This applies a unique label to the module, allowing it to be isolated when
    necessary

In Compose files where multiple containers are defined, all containers should be
labeled with the same label sets (as seen in the
[`hive` module's](https://github.com/jefflester/minitrino/blob/master/src/lib/modules/catalog/hive/hive.yaml)
Compose file).

______________________________________________________________________

**Note**: The example above already includes a named volume (`postgres-data`) in
the Compose file. Named volumes should always have labels applied to them, as
shown in the example.

## Test the New Catalog

Provision the new catalog with the CLI:

```sh
minitrino -v provision -m my-postgres
```

Open a shell session in the `minitrino` container and run some tests:

```sh
docker exec -it minitrino-default bash
trino-cli

trino> SHOW CATALOGS;
```

**Note**: If you provisioned with a custom cluster name (e.g.,
`--cluster my-cluster`), replace `minitrino-default` with
`minitrino-my-cluster`.
