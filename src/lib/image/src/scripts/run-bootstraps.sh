#!/usr/bin/env bash

# Usage: run-bootstraps.sh [before_start|after_start]
# Defaults to before_start if not specified.

set -euxo pipefail

FUNC="${1:-before_start}"

mkdir -p /tmp/minitrino/bootstrap
if compgen -G "/mnt/bootstrap/*.sh" > /dev/null; then
    cp /mnt/bootstrap/*.sh /tmp/minitrino/bootstrap/
fi
for module_dir in /mnt/bootstrap/*/; do
    [ -d "$module_dir" ] || continue
    module_name=$(basename "$module_dir")
    mkdir -p "/tmp/minitrino/bootstrap/$module_name"
    if compgen -G "$module_dir*.sh" > /dev/null; then
        cp "$module_dir"*.sh "/tmp/minitrino/bootstrap/$module_name/"
    fi
done
chmod -R +x /tmp/minitrino/bootstrap

for script in \
    /tmp/minitrino/bootstrap/*.sh \
    /tmp/minitrino/bootstrap/*/*.sh; do
    [ -e "$script" ] || continue
    source "$script"
    if declare -f "$FUNC" > /dev/null; then
        "$FUNC" || true
    fi
    unset -f before_start || true
    unset -f after_start || true
done

chown -R "${SERVICE_USER}":root "/etc/${CLUSTER_DIST}"
chmod -R g=u "/etc/${CLUSTER_DIST}"
