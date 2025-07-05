# Iceberg Catalog

Add an [Iceberg catalog](https://trino.io/docs/current/connector/iceberg.html)
to the cluster along with MinIO object storage for storing Iceberg data and an
Iceberg REST catalog for metadata management.

## Usage

{{ persistent_storage_warning }}

```sh
minitrino provision -m iceberg
```

{{ connect_trino_cli }}

Confirm Iceberg is reachable:

```sql
SHOW SCHEMAS FROM iceberg;
```

Create a table:

```sql
CREATE TABLE iceberg.minitrino.customer
WITH (
    location = 's3a://minitrino/minitrino_iceberg/minitrino/'
)
AS SELECT * FROM tpch.tiny.customer;
```

## Dependent Modules

- [`minio`](../admin/minio.md#minio): Required for object storage.
