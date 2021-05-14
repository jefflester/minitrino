#!/usr/bin/env bash

set -euxo pipefail

echo "Downloading Ranger CLI..."
STARBURST_RANGER_CLI_PATH=/usr/local/bin/starburst-ranger-cli
DIST=${STARBURST_VER:0:3}
CLI_URL=https://s3.us-east-2.amazonaws.com/software.starburstdata.net/"${DIST}"e/"${STARBURST_VER}"/starburst-ranger-cli-"${STARBURST_VER}"-executable.jar

curl -fsSL "${CLI_URL}" > "${STARBURST_RANGER_CLI_PATH}"
chmod -v +x "${STARBURST_RANGER_CLI_PATH}"
ln -vs "${STARBURST_RANGER_CLI_PATH}" starburst-ranger-cli

echo "Waiting for Ranger Admin to come up..."
/opt/minitrino/wait-for-it.sh ranger-admin:6080 --strict --timeout=150 -- echo "Ranger Admin service is up."

echo "Initializing Ranger Admin with service, users, and policies..."
chmod -R +x /tmp/ranger

/tmp/ranger/create-service.sh
/tmp/ranger/create-users.sh
/tmp/ranger/add-user-policies.sh
