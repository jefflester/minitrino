#!/usr/bin/env bash

## Filename prefixed with 00 to ensure this runs first

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
    # Create _stub role so that the admin user auto-uses an admin-like role when
    # connecting via the trino-cli
    echo "Creating stub role..."
    role_id=$(curl -X POST \
        -H "X-Trino-User: admin" \
        -H "X-Trino-Role: system=ROLE{sysadmin}" \
        -H "Accept: application/json" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "_stub",
            "description": "Admin role used for cluster bootstrapping."
        }' \
        "http://localhost:8080/api/v1/biac/roles" | jq .id || true
    )

    if [ -z "${role_id}" ] || [ "${role_id}" = "null" ]; then
    echo "Stub role not created, attempting to look up existing stub role..."
    role_id=$(curl -s -X GET \
        -H "X-Trino-User: admin" \
        -H "X-Trino-Role: system=ROLE{sysadmin}" \
        -H "Accept: application/json" \
        "http://localhost:8080/api/v1/biac/roles" | jq -r '.result[] | select(.name=="_stub") | .id')
    fi

    echo "Assigning admin role to stub role..."
    curl -X POST \
    -H "X-Trino-User: admin" \
    -H "X-Trino-Role: system=ROLE{sysadmin}" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    -d "{
        \"roleId\": \"${role_id}\",
        \"roleAdmin\": true
    }" \
    "http://localhost:8080/api/v1/biac/subjects/users/admin/assignments" || true

    echo "Granting privs to stub role..."
    actions=(SHOW CREATE ALTER DROP EXECUTE SELECT INSERT DELETE UPDATE)
    for action in "${actions[@]}"; do
    curl -X POST \
        -H "X-Trino-User: admin" \
        -H "X-Trino-Role: system=ROLE{sysadmin}" \
        -H "Accept: application/json" \
        -H "Content-Type: application/json" \
        -d "{
        \"effect\": \"ALLOW_WITH_GRANT_OPTION\",
        \"action\": \"${action}\",
        \"entity\": {
            \"category\": \"TABLES\",
            \"allEntities\": true
        }
        }" \
        "http://localhost:8080/api/v1/biac/roles/${role_id}/grants" || true
    done
}
