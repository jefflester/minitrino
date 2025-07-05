# Hive Catalog

Add a [Hive catalog](https://trino.io/docs/current/connector/hive.html) to the
cluster along with a Hive metastore for storing table metadata and MinIO object
storage for storing table data.

## Usage

{{ persistent_storage_warning }}

```sh
minitrino provision -m hive
```

{{ connect_trino_cli }}

Confirm Hive is reachable:

```sql
SHOW SCHEMAS FROM hive;
```

Create a table:

```sql
CREATE TABLE hive.minitrino.customer 
WITH (
    location = 's3a://minitrino/minitrino_hive/'
)
AS SELECT * FROM tpch.tiny.customer;
```

## Dependent Modules

- [`minio`](../admin/minio.md#minio): Required for object storage.
