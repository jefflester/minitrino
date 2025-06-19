#!/usr/bin/env bash

set -euxo pipefail

SERVICE_USER="${1}"
SERVICE_GROUP="${2}"
SERVICE_UID="${3}"
SERVICE_GID="${4}"
TRINO_VER="${CLUSTER_VER:0:3}"

echo "Installing ${CLUSTER_DIST}-${CLUSTER_VER} for user ${SERVICE_USER} (UID=${SERVICE_UID}, GID=${SERVICE_GID})..."

create_app_user() {
    echo "Creating application user..."
    if ! id "${SERVICE_USER}" &>/dev/null; then
        useradd "${SERVICE_USER}" --uid "${SERVICE_UID}" --gid "${SERVICE_GID}"
        usermod -aG "${SERVICE_GROUP}" "${SERVICE_USER}"
        echo "${SERVICE_USER} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
    fi
}

create_directories() {
    echo "Creating application directories..."
    mkdir -p \
        /usr/lib/"${CLUSTER_DIST}"/ \
        /data/"${CLUSTER_DIST}"/ \
        /home/"${CLUSTER_DIST}"/ \
        /mnt/etc/
}

copy_scripts() {
    echo "Copying entrypoint scripts..."
    cp /tmp/copy-config.sh /usr/lib/"${CLUSTER_DIST}"/bin/
    cp /tmp/run-bootstraps.sh /usr/lib/"${CLUSTER_DIST}"/bin/
    cp /tmp/run-minitrino.sh /usr/lib/"${CLUSTER_DIST}"/bin/
}

set_ownership_and_perms() {
    echo "Setting directory ownership and permissions..."
    chown -R "${SERVICE_USER}":"${SERVICE_GROUP}" \
        /usr/lib/"${CLUSTER_DIST}" \
        /data/"${CLUSTER_DIST}" \
        /etc/"${CLUSTER_DIST}" \
        /home/"${CLUSTER_DIST}" \
        /mnt/etc
    chmod -R g=u \
        /usr/lib/"${CLUSTER_DIST}" \
        /data/"${CLUSTER_DIST}" \
        /etc/"${CLUSTER_DIST}" \
        /home/"${CLUSTER_DIST}" \
        /mnt/etc
}

configure_jvm() {
    echo "Configuring jvm.config..."
    cd /etc/"${CLUSTER_DIST}"/
    curl -#LfS -o jvm.config \
        https://raw.githubusercontent.com/trinodb/trino/"${TRINO_VER}"/core/docker/default/etc/jvm.config
    chmod g+w jvm.config
    chown "${SERVICE_USER}":"${SERVICE_GROUP}" jvm.config

    sed -i '/^-agentpath:\/usr\/lib\/trino\/bin\/libjvmkill\.so$/d' jvm.config
    echo "-Djavax.net.ssl.trustStore=/etc/${CLUSTER_DIST}/tls-jvm/cacerts" >> jvm.config
    echo "-Djavax.net.ssl.trustStorePassword=changeit" >> jvm.config

    if grep -qE '^-XX:(InitialRAMPercentage|MaxRAMPercentage)' jvm.config; then
        line_num=$(grep -nE '^-XX:(InitialRAMPercentage|MaxRAMPercentage)' \
            jvm.config | head -n1 | cut -d: -f1)
        sed -i '/^-XX:InitialRAMPercentage/d' jvm.config
        sed -i '/^-XX:MaxRAMPercentage/d' jvm.config
        sed -i "${line_num}i-Xmx1G\n-Xms1G" jvm.config
    else
        echo "-Xmx1G" >> jvm.config
        echo "-Xms1G" >> jvm.config
    fi
}

configure_node_props() {
    echo "Configuring node.properties..."
    sed -i \
    -e "s|^node\.data-dir=.*|node.data-dir=/data/${CLUSTER_DIST}|" \
    -e "s|^plugin\.dir=.*|plugin.dir=/usr/lib/${CLUSTER_DIST}/plugin|" \
    "/etc/${CLUSTER_DIST}/node.properties"
}

install_java() {
    echo "Installing Java..."
    bash /tmp/install-java.sh "${SERVICE_USER}" "${SERVICE_GROUP}"
}

install_trino_cli() {
    echo "Installing trino-cli..."
    TRINO_CLI_PATH="/usr/local/bin/trino-cli"
    curl -#LfS -o "${TRINO_CLI_PATH}" \
        "https://repo1.maven.org/maven2/io/trino/trino-cli/${TRINO_VER}/trino-cli-${TRINO_VER}-executable.jar"
    chmod +x "${TRINO_CLI_PATH}"
    chown "${SERVICE_USER}":"${SERVICE_GROUP}" "${TRINO_CLI_PATH}"
}

install_wait_for_it() {
    echo "Installing wait-for-it..."
    WAIT_FOR_IT="/usr/local/bin/wait-for-it"
    WAIT_FOR_IT_URL="https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh"
    curl -fsSL "${WAIT_FOR_IT_URL}" > "${WAIT_FOR_IT}"
    chmod +x "${WAIT_FOR_IT}"
    chown "${SERVICE_USER}":"${SERVICE_GROUP}" "${WAIT_FOR_IT}"
}

cleanup() {
    echo "Cleaning up /tmp/ and apt cache..."
    rm -rf /tmp/*
    apt-get clean && rm -rf /var/lib/apt/lists/*
}

main() {
    create_app_user
    create_directories
    copy_scripts
    set_ownership_and_perms
    configure_jvm
    configure_node_props
    install_java
    install_trino_cli
    install_wait_for_it
    cleanup
}

main
