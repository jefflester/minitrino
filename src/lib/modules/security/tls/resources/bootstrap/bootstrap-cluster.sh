#!/usr/bin/env bash

set -euxo pipefail

before_start() {
	echo "Setting variables..."
	SSL_DIR=/mnt/etc/tls

	echo "Removing pre-existing SSL resources..."
	rm -rf "${SSL_DIR}"/* 

	echo "Generating keystore file..."
	keytool -genkeypair \
		-alias minitrino \
		-keyalg RSA \
		-keystore "${SSL_DIR}"/keystore.jks \
		-keypass changeit \
		-storepass changeit \
		-dname "CN=*.minitrino.com" \
		-ext san=dns:minitrino,dns:localhost

	echo "Adding keystore and truststore in ${SSL_DIR}..."
	keytool -export \
		-alias minitrino \
		-keystore "${SSL_DIR}"/keystore.jks \
		-rfc \
		-file "${SSL_DIR}"/minitrino_cert.cer \
		-storepass changeit \
		-noprompt

	keytool -import -v \
		-trustcacerts \
		-alias minitrino_trust \
		-file "${SSL_DIR}"/minitrino_cert.cer \
		-keystore "${SSL_DIR}"/truststore.jks \
		-storepass changeit \
		-noprompt

	# Import server cert into JVM truststore
	keytool -import -v \
		-trustcacerts \
		-alias minitrino_trust \
		-file "${SSL_DIR}"/minitrino_cert.cer \
		-keystore /etc/"${CLUSTER_DIST}"/tls-jvm/cacerts \
		-storepass changeit \
		-noprompt

	# Synchronize generated TLS artifacts to /etc/${CLUSTER_DIST}/tls
	cp -a "${SSL_DIR}/." "/etc/${CLUSTER_DIST}/tls/"
}

after_start() {
    :
}
