# Delta Lake Catalog Module

This module deploys the necessary components for a Delta Lake environment.

- **Metastore**: served via a Hive metastore (`metastore-delta-lake` container
  backed by `postgres-delta-lake` for storage)
  - The HMS image is based off of naushadh's repository
    [here](https://github.com/naushadh/hive-metastore) (refer to his repository
    for additional documentation on the HMS image and configuration options)

This module uses the Delta Lake connector. There is no Spark backend, so tables
need to be created via `CREATE TABLE AS ...` queries through the `delta`
catalog. Example:

```sql
CREATE TABLE delta.default.customer 
WITH (
    location = 's3a://minitrino/wh/default/'
)
AS SELECT * FROM tpch.tiny.customer;
```

This will create the table `delta.default.customer` and a corresponding
`_delta_log` directory in MinIO object storage.

## Usage

```sh
minitrino -v provision -m delta-lake
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m delta-lake

docker exec -it minitrino bash 
trino-cli

trino> SHOW SCHEMAS FROM delta;
```

## Persistent Storage

This module uses named volumes to persist MinIO and metastore data:

```yaml
volumes:
  postgres-delta-lake-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.delta-lake=true
```

The user-facing implication is that the data in the Hive metastore is retained
even after shutting down and/or removing the environment's containers. Minitrino
issues a warning about this whenever a module with named volumes is deployed––be
sure to look out for these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.catalog.delta-lake=true
```
