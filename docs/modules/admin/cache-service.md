# Cache Service

Add a [cache service](https://docs.starburst.io/latest/admin/cache-service.html)
to the cluster.

The module also configures
[table scan redirections](https://docs.starburst.io/latest/admin/cache-service.html#enable-table-scan-redirections)
and
[materialized views](https://docs.starburst.io/latest/connector/starburst-hive.html#materialized-views).

## Usage

{{ starburst_license_warning }}

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m cache-service
```

The following catalogs are configured:

- `cache_svc`: Exposes the backend database for the cache service for querying
  in Starburst.
- `hive_mv_tsr`: Based on the `hive` catalog but with materialized views and
  `hive.security=allow-all` enabled.

The bootstrap script enables debug logging for `com.starburstdata.cache` as well
as JMX dump tables for the MBeans associated with the cache service. The JMX
dump tables can be queried in the `jmx.history` schema.

### Automatic Example Data and Schema Creation

Upon provisioning, the bootstrap script will:

- Create and populate `postgres.public.customer` and `postgres.public.orders`
  with TPCH data.
- Create Hive schemas in the `hive_mv_tsr` catalog for cache and materialized
  views.
- Create an example materialized view in `hive_mv_tsr.mvs.example`.

This ensures the cache service and table scan redirections are immediately
testable.

## Dependent Modules

- [`postgres`](../catalog/postgres.md#postgres-catalog): Used as a redirect
  source for table scan redirections.
- [`hive`](../catalog/hive.md#hive-catalog): Required for the `hive_mv_tsr`
  catalog (includes MinIO for object storage).
- [`insights`](./insights.md#insights): Enables the Starburst web UI and
  configures a backend database for persisting cache service configuration.
