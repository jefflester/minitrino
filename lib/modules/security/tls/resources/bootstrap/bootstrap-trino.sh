#!/usr/bin/env bash

set -euxo pipefail

echo "Setting variables..."
SSL_DIR=/etc/starburst/ssl

echo "Removing pre-existing SSL resources..."
rm -f "${SSL_DIR}"/* 

echo "Generating keystore file..."
keytool -genkeypair \
	-alias trino \
	-keyalg RSA \
	-keystore "${SSL_DIR}"/keystore.jks \
	-keypass changeit \
	-storepass changeit \
	-dname "CN=*.starburstdata.com" \
	-ext san=dns:trino.minitrino.starburstdata.com,dns:trino,dns:localhost

echo "Adding keystore and truststore in ${SSL_DIR}..."
keytool -export \
	-alias trino \
	-keystore "${SSL_DIR}"/keystore.jks \
	-rfc \
	-file "${SSL_DIR}"/trino_certificate.cer \
	-storepass changeit \
	-noprompt

keytool -import -v \
	-trustcacerts \
	-alias trino_trust \
	-file "${SSL_DIR}"/trino_certificate.cer \
	-keystore "${SSL_DIR}"/truststore.jks \
	-storepass changeit \
	-noprompt
