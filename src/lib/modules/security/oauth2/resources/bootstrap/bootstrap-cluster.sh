#!/usr/bin/env bash

set -euxo pipefail

before_start() {
    echo "Fetching OAuth2 server certificate..."
    openssl s_client -connect oauth2-server:8100 2>/dev/null </dev/null \
        | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' \
        > /tmp/oauth2-server.pem

    echo "Adding OAuth2 server certificate to truststore..."
    if ! keytool -list \
        -keystore /etc/starburst/tls-jvm/cacerts \
        -storepass changeit \
        -alias oauth2-server > /dev/null 2>&1
    then
        keytool -import -noprompt -trustcacerts \
            -storepass changeit \
            -alias oauth2-server \
            -file /tmp/oauth2-server.pem \
            -keystore /etc/"${CLUSTER_DIST}"/tls-jvm/cacerts
    else
        echo "Alias 'oauth2-server' already exists in truststore. Skipping import."
    fi

    oauth_debug="io.trino.server.security.oauth2=DEBUG"
    ui_debug="io.trino.server.ui.OAuth2WebUiAuthenticationFilter=DEBUG"
    if ! grep -q "${oauth_debug}" /etc/"${CLUSTER_DIST}"/log.properties; then
        echo "${oauth_debug}" >> /etc/"${CLUSTER_DIST}"/log.properties
    fi
    if ! grep -q "${ui_debug}" /etc/"${CLUSTER_DIST}"/log.properties; then
        echo "${ui_debug}" >> /etc/"${CLUSTER_DIST}"/log.properties
    fi
}

after_start() {
    :
}
