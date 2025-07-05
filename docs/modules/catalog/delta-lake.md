# Delta Lake Catalog

Add a [Delta Lake
catalog](https://trino.io/docs/current/connector/delta-lake.html) to the cluster
along with a Hive metastore for storing table metadata and MinIO object storage
for storing table data.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m delta-lake
```

{{ connect_trino_cli }}

Confirm Delta Lake is reachable:

```sql
SHOW SCHEMAS FROM delta;
```

Create a table:

```sql
CREATE TABLE delta.minitrino.customer 
WITH (
    location = 's3a://minitrino/minitrino_delta_lake/minitrino/'
)
AS SELECT * FROM tpch.tiny.customer;
```

This will create the table `delta.minitrino.customer` and a corresponding
`_delta_log` directory in MinIO object storage.

## Dependent Modules

- [`minio`](../admin/minio.md#minio): Required for object storage.
