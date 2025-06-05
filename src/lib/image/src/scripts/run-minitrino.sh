#!/usr/bin/env bash

set -euxo pipefail

main() {
    local pipe="/tmp/launcher-log.pipe"
    mkdir /etc/"${CLUSTER_DIST}"/.minitrino || true
    /usr/lib/"${CLUSTER_DIST}"/bin/copy-config.sh
    /usr/lib/"${CLUSTER_DIST}"/bin/run-bootstraps.sh before_start

    rm -f "${pipe}"
    mkfifo "${pipe}"

    start_service "${pipe}" "$@"
    post_start "${pipe}"

    local log_monitor_pid=$!
    wait "${launcher_pid}"
    wait "${log_monitor_pid}"
    rm -f "${pipe}"
}

post_start() {
    local pipe="$1"
    local found_started=0
    (
        set +x
        while IFS= read -r line; do
            echo "${line}"
            if [[ ${found_started} -eq 0 && "${line}" == *"SERVER STARTED"* ]]; then
                found_started=1
                /usr/lib/"${CLUSTER_DIST}"/bin/run-bootstraps.sh after_start
            fi
        done < "${pipe}"
    ) &
}

start_service() {
    local pipe="$1"
    shift
    ulimit -c 4096
    rm -f "/data/${CLUSTER_DIST}/var/run/launcher.pid"
    local launcher_opts=(--etc-dir "/etc/${CLUSTER_DIST}")
    if ! grep -s -q 'node.id' "/etc/${CLUSTER_DIST}/node.properties"; then
        launcher_opts+=("-Dnode.id=${HOSTNAME}")
    fi
    exec gosu "${SERVICE_USER}" \
        "/usr/lib/${CLUSTER_DIST}/bin/launcher" \
        run "${launcher_opts[@]}" "$@" > "${pipe}" 2>&1 &
    launcher_pid=$!
}

main "$@"
