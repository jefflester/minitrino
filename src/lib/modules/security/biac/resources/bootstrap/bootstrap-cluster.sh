#!/usr/bin/env bash

set -euxo pipefail

CATALOG_DIR="/etc/${CLUSTER_DIST}/catalog"

for file in "$CATALOG_DIR"/*.properties; do
    if grep -q "^connector.name=hive" "$file"; then
        echo "Adding hive.security=starburst to $file"
        echo "hive.security=starburst" >> "$file"
    fi

    if grep -q "^connector.name=delta-lake" "$file"; then
        echo "Adding delta.security=starburst to $file"
        echo "delta.security=starburst" >> "$file"
    fi

    if grep -q "^connector.name=iceberg" "$file"; then
        echo "Adding iceberg.security=system to $file"
        echo "iceberg.security=system" >> "$file"
    fi
done
