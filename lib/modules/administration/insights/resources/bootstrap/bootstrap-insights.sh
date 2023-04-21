#!/usr/bin/env bash

set -euxo pipefail

echo "Adding Trino configs..."
cat <<EOT >> /etc/starburst/config.properties
insights.jdbc.url=jdbc:postgresql://postgres-query-logger:5432/querylogger
insights.jdbc.user=admin
insights.jdbc.password=trinoRocks15
insights.persistence-enabled=true
insights.metrics-persistence-enabled=true
#insights.authorized-users=.*
EOT