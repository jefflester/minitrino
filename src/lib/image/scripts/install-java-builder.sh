#!/usr/bin/env bash

set -euxo pipefail

SERVICE_USER="${1}"
CLUSTER_VER="${2}"
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
JAVA_MATRIX="${SCRIPT_DIR}/java-matrix.json"

# Extract numeric version from version string (e.g., "474-e.8" -> "474").
# Avoid a fixed-width truncation that would break for versions >= 1000.
TRINO_VER=$(echo "${CLUSTER_VER}" | sed 's/-.*//')

echo "Detected Trino version: ${TRINO_VER}"

JAVA_VER=$(jq -r --argjson ver "${TRINO_VER}" \
    '.[] | select(.min_trino <= $ver and (.max_trino == null or .max_trino >= $ver)) | .java_full' \
    "${JAVA_MATRIX}")

if [ -z "${JAVA_VER}" ] || [ "${JAVA_VER}" = "null" ]; then
    echo "Unsupported Trino version: ${TRINO_VER}. Exiting..."
    exit 1
fi

echo "Installing Java version ${JAVA_VER} for user ${SERVICE_USER}..."
su - "${SERVICE_USER}" -c "bash -lc 'curl -s https://get.sdkman.io | bash'"
su - "${SERVICE_USER}" -c \
    "bash -lc 'source ~/.sdkman/bin/sdkman-init.sh && \
    sdk install java ${JAVA_VER}-tem --disableUsage && \
    sdk flush temp && \
    sdk flush archives && \
    sdk flush broadcast && \
    rm -rf ~/.sdkman/tmp/* ~/.sdkman/archives/*'"

echo "Copying cacerts for TLS..."
USER_HOME=$(eval echo "~${SERVICE_USER}")
CACERTS_PATH=$(find "${USER_HOME}/.sdkman/candidates/java/" -type f -name 'cacerts' 2>/dev/null | head -n 1)
if [[ -z "${CACERTS_PATH}" ]]; then
    echo "Could not find cacerts file. Exiting..."
    exit 1
fi

mkdir -p /tmp/tls-jvm/
cp "${CACERTS_PATH}" /tmp/tls-jvm/
chmod 644 /tmp/tls-jvm/cacerts

echo "Java installation complete!"
