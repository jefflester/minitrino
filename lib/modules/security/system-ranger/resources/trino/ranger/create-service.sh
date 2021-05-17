#!/usr/bin/env bash

set -ex

function create_sep_service() {
    echo "Creating Starburst Ranger service..."
    curl -i -v POST -u admin:trinoRocks15 --header "Content-Type: application/json" --header "Accept: application/json" -d '
    {
      "name":"starburst",
      "description":"Starburst Ranger service",
      "isEnabled":true,
      "tagService":"",
      "configs":{
          "username":"starburst_service",
          "password":"",
          "jdbc.driverClassName":"io.prestosql.jdbc.PrestoDriver",
          "jdbc.url":"jdbc:presto://trino:8080",
          "resource-lookup":"true",
          "commonNameForCertificate":""
    },
    "type":"starburst-enterprise"
    }
    ' \
    "http://ranger-admin:6080/service/plugins/services";
}

COUNTER=0 && set +e
while [[ "${COUNTER}" -le 61 ]]; do 
    if create_sep_service | grep -q "HTTP/1.1 200 OK"; then
        break
    elif [[ "${COUNTER}" == 61 ]]; then
        echo "Timed out waiting for Ranger Admin"
        exit 1
    else 
        sleep 1
        ((COUNTER++))
    fi
done
set -e
