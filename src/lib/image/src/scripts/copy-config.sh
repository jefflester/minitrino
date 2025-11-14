#!/usr/bin/env bash

set -euxo pipefail

push_status="$(cat /etc/"${CLUSTER_DIST}"/.minitrino/push-config-status.txt 2>/dev/null || echo "")"
cp_mnt_status="$(cat /etc/"${CLUSTER_DIST}"/.minitrino/copy-mnt-status.txt 2>/dev/null || echo "")"

if [ "${push_status}" == "ACTIVE" ]; then
    echo "Copying pushed configs..."
    cp -R /tmp/etc/* /etc/"${CLUSTER_DIST}"/
    echo "INACTIVE" > /etc/"${CLUSTER_DIST}"/.minitrino/push-config-status.txt
else
    if [ "${cp_mnt_status}" == "FINISHED" ]; then
        echo "Configs were previously copied. Not overwriting with mounted (default) configs."
    else
        if compgen -G "/mnt/etc/*" > /dev/null; then
            cp -R /mnt/etc/* /etc/"${CLUSTER_DIST}"/
            echo "FINISHED" > /etc/"${CLUSTER_DIST}"/.minitrino/copy-mnt-status.txt
        fi
    fi
fi
