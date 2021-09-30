#!/usr/bin/env bash

echo "Adding Trino configs..."
cat <<EOT >> /etc/starburst/config.properties
insights.persistence-enabled=true
insights.metrics-persistence-enabled=true
insights.jdbc.url=jdbc:postgresql://postgres-event-logger:5432/event_logger
insights.jdbc.user=admin
insights.jdbc.password=trinoRocks15
insights.authorized-users=.*
EOT
