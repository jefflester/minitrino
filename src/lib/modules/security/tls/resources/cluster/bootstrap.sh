#!/usr/bin/env bash

set -euxo pipefail

before_start() {
    local ssl_dir=/mnt/etc/tls
    local san_hostname

    if [[ -n "${HOSTNAME}" ]]; then
        san_hostname="${HOSTNAME}"
    else
        san_hostname="minitrino-${CLUSTER_NAME}"
    fi

    generate_tls_assets() {
        echo "Generating new TLS artifacts in ${ssl_dir}..."
        rm -rf "${ssl_dir:?}"/*
        keytool -genkeypair \
            -alias minitrino \
            -keyalg RSA \
            -keystore "${ssl_dir}/keystore.jks" \
            -keypass changeit \
            -storepass changeit \
            -validity 3650 \
            -dname "CN=*.minitrino.com" \
            -ext san=dns:minitrino,dns:localhost,dns:"${san_hostname}"
        keytool -export \
            -alias minitrino \
            -keystore "${ssl_dir}/keystore.jks" \
            -rfc \
            -file "${ssl_dir}/minitrino_cert.cer" \
            -storepass changeit \
            -noprompt
        keytool -import -v \
            -trustcacerts \
            -alias minitrino_trust \
            -file "${ssl_dir}/minitrino_cert.cer" \
            -keystore "${ssl_dir}/truststore.jks" \
            -storepass changeit \
            -noprompt
    }

    if [[ \
        -f "${ssl_dir}/keystore.jks" \
        && -f "${ssl_dir}/minitrino_cert.cer" \
        && -f "${ssl_dir}/truststore.jks" \
    ]]; then
        if keytool -list -v \
            -keystore "${ssl_dir}/keystore.jks" \
            -storepass changeit \
            -alias minitrino \
            | grep -q "DNSName: ${san_hostname}"; \
        then
            echo \
                "TLS artifacts already exist in ${ssl_dir} " \
                "and SAN ${san_hostname} is present. Skipping generation."
        else
            echo \
                "TLS artifacts exist but SAN ${san_hostname} missing. " \
                "Regenerating."
            generate_tls_assets
        fi
    else
        generate_tls_assets
    fi

    # Import server cert into JVM truststore (always do this in case JVM truststore is ephemeral)
    local alias="minitrino_trust"
    if keytool \
        -list -storepass changeit \
        -keystore /etc/"${CLUSTER_DIST}"/tls-jvm/cacerts \
        -alias "${alias}" > /dev/null 2>&1; then
        echo "Alias ${alias} already exists in JVM truststore, skipping import."
    else
        keytool -import -v \
            -trustcacerts \
            -alias "${alias}" \
            -file "${ssl_dir}/minitrino_cert.cer" \
            -keystore /etc/"${CLUSTER_DIST}"/tls-jvm/cacerts \
            -storepass changeit \
            -noprompt
    fi

    # Synchronize generated TLS artifacts to /etc/${CLUSTER_DIST}/tls
    cp -a "${ssl_dir}/." "/etc/${CLUSTER_DIST}/tls/"
}

after_start() {
    :
}
