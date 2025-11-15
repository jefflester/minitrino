#!/usr/bin/env bash

set -euxo pipefail

# Trap to print suppressed logs on any error or exit, unless already printed
trap 'if [ "${SUPPRESSED_LOGS_PRINTED:-0}" -eq 0 ]; then \
    echo "Unplanned exit. Printing suppressed logs..."; \
    print_suppressed_logs; \
    fi' ERR EXIT

main() {
    local pipe="/tmp/launcher-log.pipe"
    mkdir /etc/"${CLUSTER_DIST}"/.minitrino || true
    python3 /usr/lib/"${CLUSTER_DIST}"/bin/gen_config.py
    /usr/lib/"${CLUSTER_DIST}"/bin/copy-config.sh
    /usr/lib/"${CLUSTER_DIST}"/bin/run-bootstraps.sh before_start
    echo "---- PRE START BOOTSTRAPS COMPLETED ----"

    rm -f "${pipe}"
    mkfifo "${pipe}"

    start_service "${pipe}" "$@"
    post_start "${pipe}"

    local log_monitor_pid=$!
    wait "${launcher_pid}"
    wait "${log_monitor_pid}"
    rm -f "${pipe}"

    # Print suppressed logs at the very end (healthy path)
    print_suppressed_logs
    SUPPRESSED_LOGS_PRINTED=1
    rm -f /tmp/.server.log
}

post_start() {
    local pipe="$1"
    local found_started=0
    set +x
    while IFS= read -r line; do
        echo "${line}"
        if [[ ${found_started} -eq 0 && "${line}" == *"SERVER STARTED"* ]]; then
            found_started=1
            wait_for_query_ready
            if ! /usr/lib/"${CLUSTER_DIST}"/bin/run-bootstraps.sh after_start; then
                echo "---- ERROR: Post-start bootstraps failed. ----"
                exit 1
            else
                echo "---- POST START BOOTSTRAPS COMPLETED ----"
            fi
        fi
    done < "${pipe}"
    set -x
}

print_suppressed_logs() {
    local dist_caps="${CLUSTER_DIST^^}"
    echo "---- BEGIN ${dist_caps} SERVICE LOGS (suppressed during startup, now replayed) ----"
    if [ -f /tmp/.server.log ]; then
        cat /tmp/.server.log
    else
        echo "No buffered service log found at /tmp/.server.log"
        if [ -e /proc/1/fd/1 ]; then
            cat /proc/1/fd/1 || echo "Unable to read /proc/1/fd/1"
        fi
    fi
    echo "---- END ${dist_caps} SERVICE LOGS ----"
}

wait_for_query_ready() {
    if [ "${COORDINATOR}" != "true" ]; then
        return
    fi

    local retries="${STARTUP_SELECT_RETRIES:-30}"
    local elapsed=0

    echo "Waiting for cluster to accept queries..."
    while [ "${elapsed}" -lt "${retries}" ]; do
        if timeout 2 trino-cli --user admin --execute "SELECT 1"; then
            echo "---- CLUSTER IS READY ----"
            sleep 3 # Let plugins fully initialize
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    echo "---- ERROR: Cluster could not accept queries after ${retries} retries. ----"
    exit 1
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
    # Start the service with tee to /tmp/.server.log for early log capture
    gosu "${SERVICE_USER}" \
        "/usr/lib/${CLUSTER_DIST}/bin/launcher" \
        run "${launcher_opts[@]}" "$@" 2>&1 | tee /tmp/.server.log > "${pipe}" &
    # Note: After cluster is ready, logs are re-piped to $pipe as before

    launcher_pid=$!
}

main "$@"
