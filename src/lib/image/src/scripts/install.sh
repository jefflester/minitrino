#!/usr/bin/env bash

set -euxo pipefail

USER="${1}"
GROUP="${2}"
UID="${3}"
GID="${4}"

DIST="${STARBURST_VER:0:3}e"
TRINO_DIST="${STARBURST_VER:0:3}"
BUCKET="s3.us-east-2.amazonaws.com/software.starburstdata.net"

check_arch() {
    if [ "$TRINO_DIST" -ge 462 ]; then
        case "$(uname -m)" in
            x86_64|amd64)
                ARCH="x86_64"
                ;;
            aarch64|arm64)
                ARCH="aarch64"
                ;;
            *)
                echo "Unsupported architecture: $(uname -m)"
                exit 1
                ;;
        esac
    else
        ARCH=""
    fi
    STARBURST_VER_ARCH="${STARBURST_VER}${ARCH:+.$ARCH}"
    STARBURST_VER_ARCH_UNPACK="${STARBURST_VER}${ARCH:+-$ARCH}"
}

create_app_user() {
    echo "Creating application user..."
    useradd "${USER}" --uid "${UID}" --gid "${GID}"
    usermod -aG "${GROUP}" "${USER}"
    echo "starburst ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
}

create_directories() {
    echo "Creating application directories..."
    mkdir -p /usr/lib/starburst/ /data/starburst/ /home/starburst/
}

download_and_extract() {
    echo "Downloading application tarball..."
    cd /tmp/
    TAR_FILE="starburst-enterprise-${STARBURST_VER_ARCH}.tar.gz"
    curl "${BUCKET}/${DIST}/${STARBURST_VER}/${TAR_FILE}" --output "${TAR_FILE}"
    tar xvfz "${TAR_FILE}"
    cp -R "starburst-enterprise-${STARBURST_VER_ARCH_UNPACK}"/* /usr/lib/starburst/
}

copy_scripts() {
    echo "Copying run-starburst and run-minitrino scripts..."
    cp /tmp/run-starburst /usr/lib/starburst/bin/
    chmod +x /usr/lib/starburst/bin/run-starburst
    cp /tmp/run-minitrino.sh /usr/lib/starburst/bin/
    chmod +x /usr/lib/starburst/bin/run-minitrino.sh
}

set_ownership_and_permissions() {
    echo "Setting directory ownership and permissions..."
    chown -R "${USER}":"${GROUP}" /usr/lib/starburst/ /data/starburst/ /etc/starburst/ /home/starburst/
    chmod -R g=u /usr/lib/starburst/ /data/starburst/ /etc/starburst/ /home/starburst/
}

configure_jvm() {
    echo "Copying jvm.config..."
    cp /tmp/jvm.config /etc/starburst/
    chmod g+w /etc/starburst/jvm.config
    chown "${USER}":"${GROUP}" /etc/starburst/jvm.config
    echo "-Djavax.net.ssl.trustStore=/etc/starburst/tls-jvm/cacerts" >> /etc/starburst/jvm.config
    echo "-Djavax.net.ssl.trustStorePassword=changeit" >> /etc/starburst/jvm.config
}

install_trino_cli() {
    echo "Installing trino-cli..."
    TRINO_CLI_PATH="/usr/local/bin/trino-cli"
    CLI_URL="https://repo1.maven.org/maven2/io/trino/trino-cli/${TRINO_DIST}/trino-cli-${TRINO_DIST}-executable.jar"
    curl -fsSL "${CLI_URL}" > "${TRINO_CLI_PATH}"
    chmod +x "${TRINO_CLI_PATH}"
    chown "${USER}":"${GROUP}" "${TRINO_CLI_PATH}"
    ln -vs "${TRINO_CLI_PATH}"
}

install_wait_for_it() {
    echo "Installing wait-for-it..."
    WAIT_FOR_IT_PATH="/usr/local/bin/wait-for-it"
    WAIT_FOR_IT_URL="https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh"
    curl -fsSL "${WAIT_FOR_IT_URL}" > "${WAIT_FOR_IT_PATH}"
    chmod +x "${WAIT_FOR_IT_PATH}"
    chown "${USER}":"${GROUP}" "${WAIT_FOR_IT_PATH}"
    ln -vs "${WAIT_FOR_IT_PATH}"
}

cleanup() {
    echo "Cleaning up /tmp/..."
    rm -rf /tmp/*
}

main() {
    check_arch
    create_app_user
    create_directories
    download_and_extract
    copy_scripts
    set_ownership_and_permissions
    configure_jvm
    install_trino_cli
    install_wait_for_it
    cleanup
}

main
