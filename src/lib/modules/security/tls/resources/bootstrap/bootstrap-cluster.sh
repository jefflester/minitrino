#!/usr/bin/env bash

set -euxo pipefail

before_start() {
    SSL_DIR=/mnt/etc/tls

    if [[ -f "${SSL_DIR}/keystore.jks" && -f "${SSL_DIR}/minitrino_cert.cer" && -f "${SSL_DIR}/truststore.jks" ]]; then
        echo "TLS artifacts already exist in ${SSL_DIR}. Skipping generation."
    else
        echo "Generating new TLS artifacts in ${SSL_DIR}..."
        rm -rf "${SSL_DIR:?}"/*
        keytool -genkeypair \
            -alias minitrino \
            -keyalg RSA \
            -keystore "${SSL_DIR}/keystore.jks" \
            -keypass changeit \
            -storepass changeit \
            -validity 3650 \
            -dname "CN=*.minitrino.com" \
            -ext san=dns:minitrino,dns:localhost

        keytool -export \
            -alias minitrino \
            -keystore "${SSL_DIR}/keystore.jks" \
            -rfc \
            -file "${SSL_DIR}/minitrino_cert.cer" \
            -storepass changeit \
            -noprompt

        keytool -import -v \
            -trustcacerts \
            -alias minitrino_trust \
            -file "${SSL_DIR}/minitrino_cert.cer" \
            -keystore "${SSL_DIR}/truststore.jks" \
            -storepass changeit \
            -noprompt
    fi

    # Import server cert into JVM truststore (always do this in case JVM truststore is ephemeral)
    keytool -import -v \
        -trustcacerts \
        -alias minitrino_trust \
        -file "${SSL_DIR}/minitrino_cert.cer" \
        -keystore /etc/"${CLUSTER_DIST}"/tls-jvm/cacerts \
        -storepass changeit \
        -noprompt

    # Synchronize generated TLS artifacts to /etc/${CLUSTER_DIST}/tls
    cp -a "${SSL_DIR}/." "/etc/${CLUSTER_DIST}/tls/"
}


after_start() {
    :
}
