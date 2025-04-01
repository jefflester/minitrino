#!/usr/bin/env bash

set -euxo pipefail

# BEGIN TODO: Remove

# A breaking filesystem change was introduced in release 458. This script can be
# removed once 458 is outside the bounds of support.
# https://docs.starburst.io/458-e/object-storage/file-system-s3.html

#!/usr/bin/env bash

# A breaking filesystem change was introduced in release 458. This script can be
# removed once 458 is outside the bounds of support.
# https://docs.starburst.io/458-e/object-storage/file-system-s3.html

set -euxo pipefail

update_fs_properties() {
    local file="$1"
    echo "Updating S3 filesystem properties to use native properties in catalog: ${file}"
    sed -i 's/hive\.s3/s3/g' "${file}"
    if ! grep -q "^fs.native-s3.enabled=true" "${file}"; then
        echo "fs.native-s3.enabled=true" >> "${file}"
    fi
}

update_catalogs() {
    for file in "${CATALOG_DIR}"/*.properties; do
        connector=$(grep -E '^connector.name=' "${file}" | cut -d= -f2)

        case "${connector}" in
            hive|delta-lake|iceberg)
                update_fs_properties "${file}"
                ;;
        esac
    done
}

TRINO_DIST="${STARBURST_VER:0:3}"
CATALOG_DIR="/etc/starburst/catalog"

if [ "${TRINO_DIST}" -ge 458 ]; then
    update_catalogs
fi

# END TODO: Remove

COUNTER=0
while [ "${COUNTER}" -lt 30 ]
do
  set +e
  RESPONSE=$(curl -s -X GET -H 'Accept: application/json' -H 'X-Trino-User: admin' 'trino:8080/v1/info/')
  echo "${RESPONSE}" | grep -q '"starting":false'
  if [ $? -eq 0 ]; then
    echo "Trino health check passed."
    sleep 5
    break
  fi
  COUNTER=$((COUNTER+1))
  sleep 1
done

if [ "${COUNTER}" -eq 30 ]
then
  echo "Trino health check failed."
  exit 1
fi

set -e
echo "com.starburstdata.cache=DEBUG" >> /etc/starburst/log.properties

echo -e "jmx.dump-tables=com.starburstdata.cache.resource:name=cacheresource,\\
com.starburstdata.cache.resource:name=materializedviewsresource,\\
com.starburstdata.cache.resource:name=redirectionsresource,\\
com.starburstdata.cache:name=cleanupservice,\\
com.starburstdata.cache:name=tableimportservice
jmx.dump-period=10s
jmx.max-entries=86400" >> /etc/starburst/catalog/jmx.properties

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
