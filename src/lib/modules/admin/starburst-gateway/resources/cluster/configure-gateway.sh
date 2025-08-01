#!/usr/bin/env bash

before_start() {
    :
}

after_start() {
    set -euxo pipefail

    gateway_uri="http://starburst-gateway-${CLUSTER_NAME}:9080"

    echo "Configuring backends for Gateway at ${gateway_uri}..."

    curl -X POST "${gateway_uri}/entity" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"starburst-gateway\",
            \"proxyTo\": \"http://minitrino-${CLUSTER_NAME}:8080\",
            \"active\": true,
            \"routingGroup\": \"adhoc\",
            \"externalUrl\": \"http://localhost:60800\"
        }"

    curl -X POST "${gateway_uri}/entity" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"starburst-gateway-replica\",
            \"proxyTo\": \"http://minitrino-${CLUSTER_NAME}-dep-starburst-gateway-replica:8080\",
            \"active\": true,
            \"routingGroup\": \"adhoc\",
            \"externalUrl\": \"http://localhost:60801\"
        }"

    echo "Backends configured."
    echo "Verify by visiting ${gateway_uri}/entity or checking the Gateway UI."
}
