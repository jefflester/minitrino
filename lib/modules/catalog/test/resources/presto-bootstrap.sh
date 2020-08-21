#!/usr/bin/env bash

set -euxo pipefail

echo "Adding Presto configs..."
cat <<EOT >> /usr/lib/presto/etc/config.properties
query.max-stage-count=105
query.max-execution-time=1h
query.max-execution-time=1h
EOT