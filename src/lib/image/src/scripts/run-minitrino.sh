#!/usr/bin/env bash

set -euxo pipefail

/usr/lib/${CLUSTER_DIST}/bin/copy-config.sh

launcher_opts=(--etc-dir "/etc/${CLUSTER_DIST}")
if ! grep -s -q 'node.id' "/etc/${CLUSTER_DIST}/node.properties"; then
    launcher_opts+=("-Dnode.id=${HOSTNAME}")
fi

# Remove PID file if it exists
rm -f "/data/${CLUSTER_DIST}/var/run/launcher.pid"

ulimit -c 4096
exec "/usr/lib/${CLUSTER_DIST}/bin/launcher" run "${launcher_opts[@]}" "$@"
