#!/usr/bin/env bash

echo "Adding Trino configs..."
# Only create the file if it does not exist - we don't want to overwrite this
# file if another module has written to it
if [ ! -f /etc/starburst/cache-rules.json ]; then
cat <<EOT > /etc/starburst/cache-rules.json
{}
EOT
fi
