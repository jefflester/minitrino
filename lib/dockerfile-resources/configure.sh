#!/usr/bin/env bash

set -euxo pipefail

function configure_centos() {
    yum install -y wget \
        sudo 
    configure_base
}

function configure_redhat_ubi() {
    microdnf install wget \
        sudo \
        findutils \
        passwd
    configure_base
}

function configure_base() {
    usermod -aG wheel starburst
    echo starburst | passwd starburst --stdin
    echo "starburst ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
    CLI_URL=https://repo1.maven.org/maven2/io/trino/trino-cli/"${DIST}"/trino-cli-"${DIST}"-executable.jar
    curl -fsSL "${CLI_URL}" > "${TRINO_CLI_PATH}"
    chmod -v +x "${TRINO_CLI_PATH}"
    chown --reference=/etc/starburst/config.properties "${TRINO_CLI_PATH}"
    ln -vs "${TRINO_CLI_PATH}"
    mkdir -p /tmp/minitrino/bootstrap/after/
    mkdir /tmp/minitrino/bootstrap/before/
    echo "OK"
}

DIST="${STARBURST_VER:0:3}"

if [ "${DIST}" -le 355 ]; then
    configure_centos
else
    configure_redhat_ubi
fi
