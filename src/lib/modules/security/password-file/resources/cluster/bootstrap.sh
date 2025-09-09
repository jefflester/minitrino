#!/usr/bin/env bash

set -euxo pipefail

before_start() {
    echo "Setting up password file..."
    htpasswd -cbB -C 10 /etc/"${CLUSTER_DIST}"/password.db admin trinoRocks15
    htpasswd -bB -C 10 /etc/"${CLUSTER_DIST}"/password.db cachesvc trinoRocks15
    htpasswd -bB -C 10 /etc/"${CLUSTER_DIST}"/password.db bob trinoRocks15
    htpasswd -bB -C 10 /etc/"${CLUSTER_DIST}"/password.db alice trinoRocks15
    htpasswd -bB -C 10 /etc/"${CLUSTER_DIST}"/password.db metadata-user trinoRocks15
    htpasswd -bB -C 10 /etc/"${CLUSTER_DIST}"/password.db platform-user trinoRocks15
    htpasswd -bB -C 10 /etc/"${CLUSTER_DIST}"/password.db test trinoRocks15
}

after_start() {
	:
}
