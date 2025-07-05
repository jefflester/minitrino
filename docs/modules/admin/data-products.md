# Data Products

Configures [data products](https://docs.starburst.io/latest/data-products.html)
in the cluster.

## Usage

{{ starburst_license_warning }}

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m data-products
```

{{ connect_trino_cli }}

Verify the `backend_svc` catalog is available:

```sql
SHOW SCHEMAS FROM backend_svc;
```

When creating data product domains, use this `s3a` path, which is from a bucket
auto-provisioned in the related MinIO container:

```text
s3a://minitrino/<domain>
```

## Dependent Modules

- [`hive`](../catalog/hive.md#hive-catalog): Required for Data Products to
  function.
- [`minio`](./minio.md#minio): Required for object storage.
- [`insights`](./insights.md#insights): Enables the Starburst web UI and
  configures a backend database for persisting data product configuration.
