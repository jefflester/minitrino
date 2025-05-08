# Cache Service Module

This module configures [Starburst's cache
service](https://docs.starburst.io/latest/admin/cache-service.html) feature
along with basic config for [table scan
redirections](https://docs.starburst.io/latest/admin/cache-service.html#enable-table-scan-redirections)
and [materialized
views](https://docs.starburst.io/latest/connector/starburst-hive.html#materialized-views).

The module launches with the `postgres`, `hive`, and `insights` modules.
Additional catalogs, `cache_svc` and `hive_mv_tsr`, are also configured.
`cache_svc` exposes the backend database for the cache service for querying in
Starburst, and `hive_mv_tsr` is a clone of the `hive` catalog but with
materialized views and `hive.security=allow-all` enabled.

For troubleshooting, the bootstrap script enables debug logging for
`com.starburstdata.cache` as well as JMX dump tables for the MBeans associated
with the cache service. The JMX dump tables can be queried in the `jmx.history`
schema.

## Usage

```sh
minitrino -v provision -m cache-service
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m cache-service
```

## Table Scan Redirections (TSRs)

The `rules.json` file configures two tables for TSRs: `postgres.public.customer`
and `postgres.public.orders`. Additional tables can be specified for TSRs by
updating the `rules.json` file. The container logs will display the various
cache service operations as they occur.

## Materialized Views (MVs)

An example MV is created in `hive_mv_tsr.mvs.example`. Any number of MVs can be
added to this catalog, and MVs can pull data from any data source.
