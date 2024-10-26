#!/usr/bin/env bash

set -euxo pipefail

echo "Fetching OAuth2 server certificate..."
openssl s_client -connect oauth2-server:8100 2>/dev/null </dev/null \
    | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' \
    > /tmp/oauth2-server.pem

echo "Adding OAuth2 server certificate to truststore..."
sudo keytool -import -noprompt -trustcacerts \
    -storepass changeit \
    -alias oauth2-server \
    -file /tmp/oauth2-server.pem \
    -keystore /etc/starburst/tls-jvm/cacerts
