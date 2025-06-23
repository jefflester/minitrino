# MariaDB Catalog Module

This module provisions a standalone MariaDB service. By default, it is exposed
to the internal Docker network only via:

```yaml
ports:
  - :3306
```

To expose it at the host level, add a port to the left of the colon, e.g.:

```yaml
ports:
  - 3307:3306
```

This will allow you to connect to the service from any SQL client that supports
MariaDB drivers on `localhost:3307`. Note that a unique port (`3307`) was used
here as the MySQL module already claims the host port `3306`.

## Usage

```sh
minitrino -v provision -m mariadb
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m mariadb

docker exec -it minitrino bash 
trino-cli

trino> SHOW SCHEMAS FROM mariadb;
```

## Persistent Storage

This module uses named volumes to persist MariaDB data:

```yaml
volumes:
  mariadb-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.mariadb=true
```

The user-facing implication is that MariaDB data is retained even after shutting
down and/or removing the environment's containers. Minitrino issues a warning
about this whenever a module with named volumes is deployed––be sure to look out
for these warnings:

```text
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.catalog.mariadb=true
```

Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_mariadb-data
```
