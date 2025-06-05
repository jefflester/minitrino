#!/usr/bin/env bash

set -euxo pipefail

timeout=30
elapsed=0
status_file="/etc/${CLUSTER_DIST}/.minitrino/append-config-status.txt"

while [ $elapsed -lt $timeout ]; do
    if [ -f "$status_file" ] && grep -qx "FINISHED" "$status_file"; then
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

if [ $elapsed -eq $timeout ]; then
    echo "Timed out waiting for $status_file to contain FINISHED"
    exit 1
fi

if [ -f /mnt/license/starburstdata.license ]; then
    cp /mnt/license/starburstdata.license /etc/${CLUSTER_DIST}/starburstdata.license
fi

push_status="$(cat /etc/${CLUSTER_DIST}/.minitrino/push-config-status.txt 2>/dev/null || echo "")"

if [ "${push_status}" == "ACTIVE" ]; then
    cp -R /tmp/etc/* /etc/${CLUSTER_DIST}/
    echo "INACTIVE" > /etc/${CLUSTER_DIST}/.minitrino/push-config-status.txt
elif [ "${push_status}" == "INACTIVE" ]; then
    echo "Configs were previously pushed. Not overwriting with mounted (default) configs."
else
    if compgen -G "/mnt/etc/*" > /dev/null; then
        cp -R /mnt/etc/* /etc/${CLUSTER_DIST}/
    fi
fi
