#!/usr/bin/env bash

set -euxo pipefail

push_status="$(cat /tmp/push-config-status.txt 2>/dev/null || echo "")"

if [ "${push_status}" == "ACTIVE" ]; then
    cp -R /tmp/etc/* /etc/${CLUSTER_DIST}/
    echo "INACTIVE" > /tmp/push-config-status.txt
elif [ "${push_status}" == "INACTIVE" ]; then
    echo "Configs were previously pushed. Not overwriting with mounted (default) configs."
else
    if compgen -G "/mnt/etc/*" > /dev/null; then
        cp -R /mnt/etc/* /etc/${CLUSTER_DIST}/
    fi
fi

# Always copy license if it exists regardless of push status
if [ -f /mnt/license/starburstdata.license ]; then
    cp /mnt/license/starburstdata.license /etc/${CLUSTER_DIST}/starburstdata.license
fi

chown -R "${BUILD_USER}":root "/etc/${CLUSTER_DIST}"
chmod -R g=u "/etc/${CLUSTER_DIST}"
