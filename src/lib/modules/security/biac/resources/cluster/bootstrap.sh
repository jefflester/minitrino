#!/usr/bin/env bash

set -euxo pipefail

before_start() {
    echo "Setting the security mode of relevant catalogs to 'starburst'..."
    for file in /etc/"${CLUSTER_DIST}"/catalog/*.properties; do
        if grep -q "^connector.name=hive" "${file}"; then
            echo "Adding hive.security=starburst to ${file}"
            echo "hive.security=starburst" >> "${file}"
        fi
        if grep -q "^connector.name=delta-lake" "${file}"; then
            echo "Adding delta.security=starburst to ${file}"
            echo "delta.security=starburst" >> "${file}"
        fi
        if grep -q "^connector.name=iceberg" "${file}"; then
            echo "Adding iceberg.security=system to ${file}"
            echo "iceberg.security=system" >> "${file}"
        fi
    done
}

after_start() {
    :
}
