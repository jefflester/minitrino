# ClickHouse Catalog Module

This module provisions a ClickHouse server with some preloaded data. The
preloaded tables are stored in the `minitrino` ClickHouse database, which is
exposed as the `clickhouse.minitrino` schema in the cluster's `clickhouse`
catalog.

## Loading Data

Data is loaded by mounting a shell script to the ClickHouse container's
`docker-entrypoint-initdb.d/` directory. Scripts in this directory are executed
whenever the container boots up, and is the ClickHouse-supported method for
bootstrapping ClickHouse containers.

The init script can be edited in the library to load different tables and/or
additional data:

```sh
lib/modules/catalog/clickhouse/resources/clickhouse/init.sh
```

## Usage

```sh
minitrino -v provision -m clickhouse
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m clickhouse

docker exec -it minitrino bash 
trino-cli

trino> SHOW TABLES IN clickhouse.minitrino;
```

## Persistent Storage

This module uses named volumes to persist ClickHouse data:

```yaml
volumes:
  clickhouse-data:
    labels:
      - org.minitrino=root
      - org.minitrino.module=catalog-clickhouse
```

The user-facing implication is that ClickHouse data is retained even after
shutting down and/or removing the environment's containers. Minitrino issues a
warning about this whenever a module with named volumes is deployed––be sure to
look out for these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module=catalog-clickhouse
```
  
Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_clickhouse-data
```
