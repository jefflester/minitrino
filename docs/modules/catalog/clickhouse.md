# ClickHouse Catalog

Add a
[ClickHouse catalog](https://trino.io/docs/current/connector/clickhouse.html) to
the cluster along with ClickHouse backend.

The module provisions a ClickHouse server with some preloaded data. The
preloaded tables are stored in the `minitrino` ClickHouse database, which is
exposed as the `clickhouse.minitrino` schema in the cluster's `clickhouse`
catalog.

## Loading Data

Data is loaded via a shell script mounted to the ClickHouse container's
`docker-entrypoint-initdb.d/` directory. The init script can be edited in the
library to load different tables and/or additional data:

```sh
lib/modules/catalog/clickhouse/resources/clickhouse/init.sh
```

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m clickhouse
```

{{ connect_trino_cli }}

Confirm the tables are loaded:

```sql
SHOW TABLES IN clickhouse.minitrino;
```
