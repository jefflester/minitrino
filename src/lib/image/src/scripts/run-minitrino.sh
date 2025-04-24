#!/usr/bin/env bash

set -euxo pipefail

ulimit -c 4096

# Remove PID file if it exists
rm -f /data/${CLUSTER_DIST}/var/run/launcher.pid

launcher_opts=(--etc-dir /etc/${CLUSTER_DIST})
if ! grep -s -q 'node.id' /etc/${CLUSTER_DIST}/node.properties; then
    launcher_opts+=("-Dnode.id=${HOSTNAME}")
fi

exec /usr/lib/${CLUSTER_DIST}/bin/launcher run "${launcher_opts[@]}" "$@"
