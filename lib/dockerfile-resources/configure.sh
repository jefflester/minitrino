#!/usr/bin/env bash

set -euxo pipefail

function configure_centos() {
    yum install -y wget \
        sudo \
        openssl \
        openldap-clients \
        httpd-tools
    configure_base
}

function configure_redhat_ubi() {
    microdnf install wget \
        sudo \
        findutils \
        passwd \
        openssl \
        openldap-clients \
        httpd-tools \
        iputils
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
    curl -fsSL https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh \
        > /opt/minitrino/wait-for-it.sh \
    chmod +x /opt/minitrino/wait-for-it.sh
    echo "OK"
}

DIST="${STARBURST_VER:0:3}"

if [ "${DIST}" -le 362 ]; then
    configure_centos
else
    configure_redhat_ubi
fi
