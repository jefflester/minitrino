# Results Cache

Adds Starburst Enterprise
[result caching](https://docs.starburst.io/latest/admin/result-caching.html) to
the cluster.

## Usage

{{ starburst_license_warning }}

Provision the module:

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m results-cache
```

{{ connect_trino_cli }}

Run a query multiple times in a row. Subsequent executions should be cached:

```sql
SELECT * FROM tpch.tiny.customer LIMIT 10;
```

## Dependent Modules

- [MinIO](./minio.md): Required for results cache storage.
- [Insights](./insights.md): Enables the Starburst web UI and configures a
  backend database for persisting results cache configuration.
