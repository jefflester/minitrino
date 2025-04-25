#!/usr/bin/env bash

set -euxo pipefail

USER="${1}"
GROUP="${2}"
UID="${3}"
GID="${4}"

echo "Installing ${CLUSTER_DIST}-${CLUSTER_VER} for user ${USER} (UID=${UID}, GID=${GID})..."

normalize_arch() {
    local raw_arch
    raw_arch="$(uname -m)"

    case "${raw_arch}" in
        amd64|x86_64)
            ARCH_SEP_S3="x86_64"
            ARCH_BIN="amd64"
            ;;
        arm64|aarch64)
            ARCH_SEP_S3="aarch64"
            ARCH_BIN="arm64"
            ;;
        *)
            echo "Unsupported architecture: ${raw_arch}"
            exit 1
            ;;
    esac
}

set_dist_version() {
    if [ "${CLUSTER_DIST}" == "trino" ]; then
        TRINO_VER="${CLUSTER_VER}"
        CLUSTER_VER_ARCH="${CLUSTER_VER}"
        CLUSTER_VER_ARCH_UNPACK="${CLUSTER_VER}"
    elif [ "${CLUSTER_DIST}" == "starburst" ]; then
        TRINO_VER="${CLUSTER_VER:0:3}"
        if [ "${TRINO_VER}" -ge 462 ]; then
            CLUSTER_VER_ARCH="${CLUSTER_VER}.${ARCH_SEP_S3}"
            CLUSTER_VER_ARCH_UNPACK="${CLUSTER_VER}-${ARCH_SEP_S3}"
        else
            CLUSTER_VER_ARCH="${CLUSTER_VER}"
            CLUSTER_VER_ARCH_UNPACK="${CLUSTER_VER}"
        fi
    else
        echo "Invalid cluster distribution. Exiting..."
        exit 1
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
    mkdir -p \
        /usr/lib/"${CLUSTER_DIST}"/ \
        /data/"${CLUSTER_DIST}"/ \
        /home/"${CLUSTER_DIST}"/
}

prune_plugins() {
    echo "Pruning unused plugins..."
    local plugin_dir="/usr/lib/${CLUSTER_DIST}/plugin"
    local keep=(
        audit-log
        clickhouse
        delta-lake
        elasticsearch
        exchange-filesystem
        exchange-hdfs
        faker
        functions-python
        generic-jdbc
        group-providers
        hive
        iceberg
        jmx
        mariadb
        memory
        mysql
        mysql-event-listener
        okta-authenticator
        opensearch
        oracle
        password-authenticators
        pinot
        postgresql
        resource-group-managers
        sep-stargate
        session-property-managers
        sqlserver
        spooling-filesystem
        starburst-functions
        starburst-hive-based-ranger
        starburst-ranger
        stargate-parallel
        thrift
        tpcds
        tpch
        warp-speed
    )
    for dir in "${plugin_dir}"/*; do
        name=$(basename "$dir")
        if [[ ! " ${keep[*]} " =~ " ${name} " ]]; then
            echo "Removing plugin: $name"
            rm -rf "$dir"
        fi
    done
}

prune() {
    echo "Pruning unnecessary application files..."
    cd /tmp/

    if [ "${CLUSTER_DIST}" == "trino" ]; then
        cp -R "trino-server-${TRINO_VER}/"* /usr/lib/"${CLUSTER_DIST}"/
        rm -rf /usr/lib/"${CLUSTER_DIST}"/bin/darwin-* /usr/lib/"${CLUSTER_DIST}"/bin/linux-*

        # Copy linux-${ARCH_BIN} if present
        if [ -d "trino-server-${TRINO_VER}/bin/linux-${ARCH_BIN}" ]; then
            cp -R "trino-server-${TRINO_VER}/bin/linux-${ARCH_BIN}" /usr/lib/"${CLUSTER_DIST}"/bin/
        fi
    else
        cp -R "starburst-enterprise-${CLUSTER_VER_ARCH_UNPACK}/"* /usr/lib/"${CLUSTER_DIST}"/
        rm -rf /usr/lib/"${CLUSTER_DIST}"/bin/darwin-* /usr/lib/"${CLUSTER_DIST}"/bin/linux-*

        # Copy linux-${ARCH_BIN} if present
        if [ -d "starburst-enterprise-${CLUSTER_VER_ARCH_UNPACK}/bin/linux-${ARCH_BIN}" ]; then
            cp -R "starburst-enterprise-${CLUSTER_VER_ARCH_UNPACK}/bin/linux-${ARCH_BIN}" /usr/lib/"${CLUSTER_DIST}"/bin/
        fi
    fi

    prune_plugins
}

download_and_extract() {
    echo "Downloading application tarball..."
    cd /tmp/
    if [ "${CLUSTER_DIST}" == "trino" ]; then
        TAR_FILE="trino-server-${TRINO_VER}.tar.gz"
        curl -#LfS -o "${TAR_FILE}" \
            "https://repo1.maven.org/maven2/io/trino/trino-server/${TRINO_VER}/trino-server-${TRINO_VER}.tar.gz"
    else
        TAR_FILE="starburst-enterprise-${CLUSTER_VER_ARCH}.tar.gz"
        curl -#LfS -o "${TAR_FILE}" \
            "https://s3.us-east-2.amazonaws.com/software.starburstdata.net/${CLUSTER_VER:0:3}e/${CLUSTER_VER}/${TAR_FILE}"
    fi
    tar xvfz "${TAR_FILE}"
    prune
}

copy_scripts() {
    echo "Copying run-minitrino scripts..."
    cp /tmp/run-minitrino.sh /usr/lib/"${CLUSTER_DIST}"/bin/
}

set_ownership_and_perms() {
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
    curl -#LfS -o jvm.config \
        https://raw.githubusercontent.com/trinodb/trino/"${TRINO_VER}"/core/docker/default/etc/jvm.config
    chmod g+w jvm.config
    chown "${USER}":"${GROUP}" jvm.config
    sed -i '/^-agentpath:\/usr\/lib\/trino\/bin\/libjvmkill\.so$/d' jvm.config
    echo "-Djavax.net.ssl.trustStore=/etc/${CLUSTER_DIST}/tls-jvm/cacerts" >> jvm.config
    echo "-Djavax.net.ssl.trustStorePassword=changeit" >> jvm.config
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
    bash /tmp/install-java.sh "${USER}" "${GROUP}"
}

install_trino_cli() {
    echo "Installing trino-cli..."
    TRINO_CLI_PATH="/usr/local/bin/trino-cli"
    curl -#LfS -o "${TRINO_CLI_PATH}" \
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
    normalize_arch
    set_dist_version
    create_app_user
    create_directories
    download_and_extract
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
