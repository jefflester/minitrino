#!/usr/bin/env bash

# Trino versions and their corresponding Java versions:
# >= 436 <= 446: Java 21
# >= 447 <= 463: Java 22
# >= 464: Java 23

set -euxo pipefail

USER="${1}"
GROUP="${2}"
USER_HOME=$(eval echo "~${USER}")
TRINO_VER="${CLUSTER_VER:0:3}"

if [ "${TRINO_VER}" -ge 436 ] && [ "${TRINO_VER}" -le 446 ]; then
    JAVA_VER=21.0.5
elif [ "${TRINO_VER}" -ge 447 ] && [ "${TRINO_VER}" -le 463 ]; then
    JAVA_VER=22.0.2
elif [ "${TRINO_VER}" -ge 464 ]; then
    JAVA_VER=23.0.2
else
    echo "Unsupported Trino version. Exiting..."
    exit 1
fi

echo "Installing Java version ${JAVA_VER} for user ${USER}..."
su - "${USER}" -c "bash -lc 'curl -s https://get.sdkman.io | bash'"
su - "${USER}" -c \
    "bash -lc 'source ~/.sdkman/bin/sdkman-init.sh && \
    sdk install java ${JAVA_VER}-tem --disableUsage && \
    sdk flush temp'"

echo "Copying cacerts..."
CACERTS_PATH=$(find "${USER_HOME}/.sdkman/candidates/java/" -type f -name 'cacerts' 2> /dev/null | head -n 1)
if [[ -z "${CACERTS_PATH}" ]]; then
    echo "Could not find cacerts file. Exiting..."
    exit 1
fi

mkdir -p /etc/"${CLUSTER_DIST}"/tls-jvm/
cp "${CACERTS_PATH}" /etc/"${CLUSTER_DIST}"/tls-jvm/
chown -R "${USER}":"${GROUP}" /etc/"${CLUSTER_DIST}"/tls-jvm
chmod 644 /etc/"${CLUSTER_DIST}"/tls-jvm/cacerts
