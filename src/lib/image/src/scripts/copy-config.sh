#!/usr/bin/env bash

set -euxo pipefail

push_status="$(cat /tmp/push-config-status.txt 2>/dev/null || echo "")"

if [ "${push_status}" == "ACTIVE" ]; then
    cp -R /tmp/etc/ /etc/${CLUSTER_DIST}/
else
    cp -R /mnt/etc/ /etc/${CLUSTER_DIST}/
fi

chown -R "${BUILD_USER}":root "/etc/${CLUSTER_DIST}"
chmod -R g=u "/etc/${CLUSTER_DIST}"
