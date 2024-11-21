# ClickHouse Catalog Module

This module provisions a ClickHouse server with some preloaded data. The
preloaded tables are stored in the `minitrino` ClickHouse database, which is
exposed as the `clickhouse.minitrino` schema in Trino.

## Loading Data

Data is loaded by mounting a shell script to the ClickHouse container's
`docker-entrypoint-initdb.d/` directory. Scripts in this directory are executed
whenever the container boots up, and is the ClickHouse-supported method for
bootstrapping ClickHouse containers.

The init script can be edited in the library to load different tables and/or
additional data:

    lib/modules/catalog/clickhouse/resources/clickhouse/init.sh

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module clickhouse
    docker exec -it trino bash 
    trino-cli
    trino> show tables in clickhouse.minitrino;
