#!/usr/bin/env bash

set -euxo pipefail

before_start() {
  echo "com.starburstdata.cache=DEBUG" >> /etc/"${CLUSTER_DIST}"/log.properties

  echo -e "jmx.dump-tables=com.starburstdata.cache.resource:name=cacheresource,\\
  com.starburstdata.cache.resource:name=materializedviewsresource,\\
  com.starburstdata.cache.resource:name=redirectionsresource,\\
  com.starburstdata.cache:name=cleanupservice,\\
  com.starburstdata.cache:name=tableimportservice
  jmx.dump-period=10s
  jmx.max-entries=86400" >> /etc/"${CLUSTER_DIST}"/catalog/jmx.properties
}

after_start() {
  sleep 5 # Let catalogs finish initialization

  echo "Creating Postgres tables..."
  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE TABLE IF NOT EXISTS postgres.public.customer AS SELECT * FROM tpch.tiny.customer"

  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE TABLE IF NOT EXISTS postgres.public.orders AS SELECT * FROM tpch.tiny.orders"

  echo "Creating Hive cache schema (for table scan redirections)..."
  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE SCHEMA IF NOT EXISTS hive_mv_tsr.cache WITH (LOCATION = 's3a://minitrino/cache/')"

  echo "Creating materialized view schemas..."
  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE SCHEMA IF NOT EXISTS hive_mv_tsr.mv_storage WITH (LOCATION = 's3a://minitrino/mv/mv_storage/')"
  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE SCHEMA IF NOT EXISTS hive_mv_tsr.mvs WITH (LOCATION = 's3a://minitrino/mv/mvs/')"

  echo "Creating materialized views..."
  QUERY="CREATE OR REPLACE MATERIALIZED VIEW hive_mv_tsr.mvs.example
  WITH (
    partitioned_by = ARRAY['orderdate'],
    max_import_duration = '1m',
    refresh_interval = '5m',
    grace_period = '10m'
  )
  AS
  (SELECT orderkey, orderdate FROM tpch.tiny.orders LIMIT 500)
  UNION ALL
  (SELECT orderkey, orderdate FROM tpch.tiny.orders LIMIT 500)"

  trino-cli --user admin --output-format TSV_HEADER --execute "${QUERY}"
}
