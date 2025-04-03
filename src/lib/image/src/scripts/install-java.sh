#!/usr/bin/env bash

# Trino versions and their corresponding Java versions:
# >= 436 <= 446: Java 21
# >= 447 <= 463: Java 22
# >= 464: Java 23

set -euxo pipefail

USER_HOME=$(eval echo "~$1")
TRINO_DIST="${STARBURST_VER:0:3}"

if [ "${TRINO_DIST}" -ge 436 ] && [ "${TRINO_DIST}" -le 446 ]; then
    JAVA_VER=21.0.5
elif [ "${TRINO_DIST}" -ge 447 ] && [ "${TRINO_DIST}" -le 463 ]; then
    JAVA_VER=22.0.1
elif [ "${TRINO_DIST}" -ge 464 ]; then
    JAVA_VER=23.0.2
else
    echo "Invalid Trino version. Exiting..."
    exit 1
fi

echo "Installing Java version ${JAVA_VER} for user $1"

curl -s https://get.sdkman.io | bash

bash -c "
source ${USER_HOME}/.sdkman/bin/sdkman-init.sh && \
sdk install java ${JAVA_VER}-tem --disableUsage && \
sdk flush temp
"

echo "Copying cacerts..."
mkdir /etc/starburst/tls-jvm/
cp "$(find "${USER_HOME}" -type f -name 'cacerts' 2> /dev/null)" /etc/starburst/tls-jvm/
chown "${USER}":"${GROUP}" /etc/starburst/tls-jvm/cacerts
chmod 644 /etc/starburst/tls-jvm/cacerts
