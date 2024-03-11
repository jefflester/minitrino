#!/usr/bin/env bash

# Trino versions and their corresponding Java versions:
# >= 413 <= 435: Java 17
# >= 436 <= 446: Java 21
# >= 447: Java 22

set -euxo pipefail

TRINO_DIST="${STARBURST_VER:0:3}"

if [ "$TRINO_DIST" -ge 413 ] && [ "$TRINO_DIST" -le 435 ]; then
    JAVA_VER=17
elif [ "$TRINO_DIST" -ge 436 ] && [ "$TRINO_DIST" -le 446 ]; then
    JAVA_VER=21
elif [ "$TRINO_DIST" -ge 447 ]; then
    JAVA_VER=22
else
    echo "Invalid Trino version. Exiting..."
    exit 1
fi

echo "Installing Java version $JAVA_VER"
apt-get install -y openjdk-${JAVA_VER}-jdk
