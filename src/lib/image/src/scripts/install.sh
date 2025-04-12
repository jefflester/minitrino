#!/usr/bin/env bash

set -euxo pipefail

USER="${1}"
GROUP="${2}"
UID="${3}"
GID="${4}"

echo "Installing ${CLUSTER_DIST}-${CLUSTER_VER} for user ${USER} (UID=${UID}, GID=${GID})..."

set_dist_version() {
    if [ "${CLUSTER_DIST}" == "trino" ]; then
        TRINO_VER="${CLUSTER_VER}"
    elif [ "${CLUSTER_DIST}" == "starburst" ]; then
        TRINO_VER="${CLUSTER_VER:0:3}"
        STARBURST_VER="${CLUSTER_VER}" # For clarity
    else
        echo "Invalid cluster distribution. Exiting..."
        exit 1
    fi
}

check_arch() {
    if [ "${TRINO_VER}" -ge 462 ]; then
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
}

create_app_user() {
    echo "Creating application user..."
    if ! id "${USER}" &>/dev/null; then
        useradd "${USER}" --uid "${UID}" --gid "${GID}"
        usermod -aG "${GROUP}" "${USER}"
        echo "${USER} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
    fi
}

create_directories() {
    echo "Creating application directories..."
    mkdir -p /usr/lib/"${CLUSTER_DIST}"/ /data/"${CLUSTER_DIST}"/ /home/"${CLUSTER_DIST}"/
}

download_and_extract() {
    echo "Downloading application tarball..."
    if [ "${CLUSTER_DIST}" == "trino" ]; then
        cd /tmp/
        TAR_FILE="trino-server-${TRINO_VER}.tar.gz"
        curl -fsSL -o "${TAR_FILE}" \
            https://repo1.maven.org/maven2/io/trino/trino-server/"${TRINO_VER}"/trino-server-"${TRINO_VER}".tar.gz
        tar xvfz "${TAR_FILE}"
        cp -R "trino-server-${TRINO_VER}"/* /usr/lib/"${CLUSTER_DIST}"/
    else # Download Starburst
        STARBURST_VER_ARCH="${STARBURST_VER}${ARCH:+.$ARCH}"
        STARBURST_VER_ARCH_UNPACK="${STARBURST_VER}${ARCH:+-$ARCH}"
        BUCKET="s3.us-east-2.amazonaws.com/software.starburstdata.net"
        TAR_FILE="starburst-enterprise-${STARBURST_VER_ARCH}.tar.gz"
        cd /tmp/
        curl -fsSL -o "${TAR_FILE}" \
            "${BUCKET}/${STARBURST_VER:0:3}/${STARBURST_VER}/${TAR_FILE}"
        tar xvfz "${TAR_FILE}"
        cp -R "starburst-enterprise-${STARBURST_VER_ARCH_UNPACK}"/* /usr/lib/"${CLUSTER_DIST}"/
    fi
}

copy_scripts() {
    echo "Copying run-minitrino scripts..."
    cp /tmp/run-minitrino.sh /usr/lib/"${CLUSTER_DIST}"/bin/
}

set_ownership_and_permissions() {
    echo "Setting directory ownership and permissions..."
    chown -R "${USER}":"${GROUP}" \
        /usr/lib/"${CLUSTER_DIST}" \
        /data/"${CLUSTER_DIST}" \
        /etc/"${CLUSTER_DIST}" \
        /home/"${CLUSTER_DIST}"
    chmod -R g=u \
        /usr/lib/"${CLUSTER_DIST}" \
        /data/"${CLUSTER_DIST}" \
        /etc/"${CLUSTER_DIST}" \
        /home/"${CLUSTER_DIST}"
}

configure_jvm() {
    echo "Configuring jvm.config..."
    cd /etc/"${CLUSTER_DIST}"/
    curl -fsSL -o jvm.config \
        https://raw.githubusercontent.com/trinodb/trino/"${TRINO_VER}"/core/docker/default/etc/jvm.config
    chmod g+w jvm.config
    chown "${USER}":"${GROUP}" jvm.config
    sed -i '/^-agentpath:\/usr\/lib\/trino\/bin\/libjvmkill\.so$/d' jvm.config
    echo "-Djavax.net.ssl.trustStore=/etc/${CLUSTER_DIST}/tls-jvm/cacerts" >> jvm.config
    echo "-Djavax.net.ssl.trustStorePassword=changeit" >> jvm.config
}

configure_node_properties() {
    echo "Configuring node.properties..."
    sed -i \
    -e "s|^node\.data-dir=.*|node.data-dir=/data/${CLUSTER_DIST}|" \
    -e "s|^plugin\.dir=.*|plugin.dir=/usr/lib/${CLUSTER_DIST}/plugin|" \
    "/etc/${CLUSTER_DIST}/node.properties"
}

install_java() {
    echo "Installing Java..."
    bash /tmp/install-java.sh "${USER}"
}

install_trino_cli() {
    echo "Installing trino-cli..."
    TRINO_CLI_PATH="/usr/local/bin/trino-cli"
    curl -fsSL -o "${TRINO_CLI_PATH}" \
        "https://repo1.maven.org/maven2/io/trino/trino-cli/${TRINO_VER}/trino-cli-${TRINO_VER}-executable.jar"
    chmod +x "${TRINO_CLI_PATH}"
    chown "${USER}":"${GROUP}" "${TRINO_CLI_PATH}"
}

install_wait_for_it() {
    echo "Installing wait-for-it..."
    WAIT_FOR_IT="/usr/local/bin/wait-for-it"
    WAIT_FOR_IT_URL="https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh"
    curl -fsSL "${WAIT_FOR_IT_URL}" > "${WAIT_FOR_IT}"
    chmod +x "${WAIT_FOR_IT}"
    chown "${USER}":"${GROUP}" "${WAIT_FOR_IT}"
}

cleanup() {
    echo "Cleaning up /tmp/ and apt cache..."
    rm -rf /tmp/*
    apt-get clean && rm -rf /var/lib/apt/lists/*
}

main() {
    set_dist_version
    check_arch
    create_app_user
    create_directories
    download_and_extract
    copy_scripts
    set_ownership_and_permissions
    configure_jvm
    configure_node_properties
    install_java
    install_trino_cli
    install_wait_for_it
    cleanup
}

main
