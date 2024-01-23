#!/usr/bin/env bash

set -euxo pipefail

USER="${1}"
GROUP="${2}"
UID="${3}"
GID="${4}"

DIST="${STARBURST_VER:0:3}"e
TRINO_DIST="${STARBURST_VER:0:3}"
BUCKET="s3.us-east-2.amazonaws.com/software.starburstdata.net"

echo "Creating Starburst user..."
useradd "${USER}" --uid "${UID}" --gid "${GID}"
usermod -aG "${GROUP}" "${USER}"
echo "starburst ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

echo "Creating Starburst directories..."
mkdir -p /usr/lib/starburst/ /data/starburst/ /home/starburst/

echo "Downloading Starburst tarball..."
cd /tmp/
curl \
    "${BUCKET}"/"${DIST}"/"${STARBURST_VER}"/starburst-enterprise-"${STARBURST_VER}".tar.gz \
    --output starburst-enterprise-"${STARBURST_VER}".tar.gz

tar xvfz /tmp/starburst-enterprise-"${STARBURST_VER}".tar.gz
cp -R /tmp/starburst-enterprise-"${STARBURST_VER}"/* /usr/lib/starburst/

echo "Copying run-starburst script..."
cp /tmp/run-starburst /usr/lib/starburst/bin/
chmod +x /usr/lib/starburst/bin/run-starburst

echo "Copying run-minitrino.sh script..."
cp /tmp/run-minitrino.sh /usr/lib/starburst/bin/
chmod +x /usr/lib/starburst/bin/run-minitrino.sh

echo "Setting directory ownership and permissions..."
chown -R "${USER}":"${GROUP}" \
    /usr/lib/starburst/ \
    /data/starburst/ \
    /etc/starburst/ \
    /home/starburst/
chmod -R g=u \
    /usr/lib/starburst/ \
    /data/starburst/ \
    /etc/starburst/ \
    /home/starburst/

echo "Installing trino-cli..."
TRINO_CLI_PATH=/usr/local/bin/trino-cli
CLI_URL=https://repo1.maven.org/maven2/io/trino/trino-cli/"${TRINO_DIST}"/trino-cli-"${TRINO_DIST}"-executable.jar

curl -fsSL "${CLI_URL}" > "${TRINO_CLI_PATH}"
chmod -v +x "${TRINO_CLI_PATH}"
chown -R "${USER}":"${GROUP}" "${TRINO_CLI_PATH}"
ln -vs "${TRINO_CLI_PATH}"

echo "Installing wait-for-it..."
WAIT_FOR_IT_PATH=/usr/local/bin/wait-for-it
WAIT_FOR_IT_URL=https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh

curl -fsSL "${WAIT_FOR_IT_URL}" > "${WAIT_FOR_IT_PATH}"
chmod -v +x "${WAIT_FOR_IT_PATH}"
chown -R "${USER}":"${GROUP}" "${WAIT_FOR_IT_PATH}"
ln -vs "${WAIT_FOR_IT_PATH}"

echo "Cleaning up /tmp/..."
rm -rf /tmp/*
