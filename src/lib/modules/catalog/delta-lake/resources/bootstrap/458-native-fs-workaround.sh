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
