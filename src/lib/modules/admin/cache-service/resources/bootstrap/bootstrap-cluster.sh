#!/usr/bin/env bash

set -euxo pipefail

before_start() {
    :
}

after_start() {
  COUNTER=0
  while [ "${COUNTER}" -lt 90 ]
  do
    set +e
    RESPONSE=$(curl -s -X GET -H 'Accept: application/json' -H 'X-Trino-User: admin' 'minitrino:8080/v1/info/')
    echo "${RESPONSE}" | grep -q '"starting":false'
    if [ $? -eq 0 ]; then
      echo "Health check passed."
      sleep 5
      break
    fi
    COUNTER=$((COUNTER+1))
    sleep 1
  done

  if [ "${COUNTER}" -eq 30 ]
  then
    echo "Health check failed."
    exit 1
  fi

  set -e
  echo "com.starburstdata.cache=DEBUG" >> /etc/${CLUSTER_DIST}/log.properties

  echo -e "jmx.dump-tables=com.starburstdata.cache.resource:name=cacheresource,\\
  com.starburstdata.cache.resource:name=materializedviewsresource,\\
  com.starburstdata.cache.resource:name=redirectionsresource,\\
  com.starburstdata.cache:name=cleanupservice,\\
  com.starburstdata.cache:name=tableimportservice
  jmx.dump-period=10s
  jmx.max-entries=86400" >> /etc/"${CLUSTER_DIST}"/catalog/jmx.properties

  echo "Creating Postgres tables..."
  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE TABLE IF NOT EXISTS postgres.public.customer AS SELECT * FROM tpch.tiny.customer"

  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE TABLE IF NOT EXISTS postgres.public.orders AS SELECT * FROM tpch.tiny.orders"

  echo "Creating Hive cache schema (for table scan redirections)..."
  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE SCHEMA IF NOT EXISTS hive_mv_tsr.cache WITH (LOCATION = 's3a://sample-bucket/cache/')"

  echo "Creating materialized view schemas..."
  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE SCHEMA IF NOT EXISTS hive_mv_tsr.mv_storage WITH (LOCATION = 's3a://sample-bucket/mv/mv_storage/')"
  trino-cli --user admin --output-format TSV_HEADER \
    --execute "CREATE SCHEMA IF NOT EXISTS hive_mv_tsr.mvs WITH (LOCATION = 's3a://sample-bucket/mv/mvs/')"

  echo "Creating materialized views..."
  QUERY="CREATE OR REPLACE MATERIALIZED VIEW hive_mv_tsr.mvs.example
  WITH (
    partitioned_by = ARRAY['orderdate'],
    max_import_duration = '1m',
    refresh_interval = '5m',
    grace_period = '10m'
  )
  AS
  SELECT orderkey, orderdate FROM tpch.tiny.orders
  UNION ALL 
  SELECT orderkey, orderdate FROM tpch.tiny.orders"

  trino-cli --user admin --output-format TSV_HEADER --execute "${QUERY}"
}
