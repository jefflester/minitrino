#!/usr/bin/env bash

set -euxo pipefail

echo "Setting variables..."
TRUSTSTORE_PATH=/etc/pki/java/cacerts
TRUSTSTORE_DEFAULT_PASS=changeit
TRUSTSTORE_PASS=trinoRocks15
KEYSTORE_PASS=trinoRocks15
SSL_DIR=/usr/lib/trino/etc/ssl

TRINO_JAVA_OPTS="-Djavax.net.ssl.trustStore=${TRUSTSTORE_PATH} \n"
TRINO_JAVA_OPTS="${TRINO_JAVA_OPTS}-Djavax.net.ssl.trustStorePassword=${TRUSTSTORE_PASS} \n"
TRINO_JAVA_OPTS="${TRINO_JAVA_OPTS}-Djavax.net.debug=ssl:handshake:verbose \n"

echo "Removing pre-existing SSL resources..."
# These should be removed prior to provisioning to ensure they do not conflate
# with other SSL resources
rm -f "${SSL_DIR}"/* 
echo "Generating keystore file..."
keytool -genkeypair \
	-alias trino \
	-keyalg RSA \
	-keystore "${SSL_DIR}"/keystore.jks \
	-keypass "${KEYSTORE_PASS}" \
	-storepass "${KEYSTORE_PASS}" \
	-dname "CN=*.starburstdata.com" \
	-ext san=dns:trino.minitrino.starburstdata.com,dns:trino,dns:localhost

echo "Change truststore password..."
keytool -storepasswd \
        -storepass "${TRUSTSTORE_DEFAULT_PASS}" \
        -new "${TRUSTSTORE_PASS}" \
        -keystore "${TRUSTSTORE_PATH}"

echo "Adding JVM configs..."
echo -e "${TRINO_JAVA_OPTS}" >> /usr/lib/trino/etc/jvm.config

echo "Adding Trino configs..."
cat <<EOT >> /usr/lib/trino/etc/config.properties
http-server.authentication.type=PASSWORD
http-server.https.enabled=true
http-server.https.port=8443
http-server.https.keystore.path=/usr/lib/trino/etc/ssl/keystore.jks
http-server.https.keystore.key=trinoRocks15
EOT

echo "Adding keystore and truststore in ${SSL_DIR}..."
keytool -export \
	-alias trino \
	-keystore "${SSL_DIR}"/keystore.jks \
	-rfc \
	-file "${SSL_DIR}"/trino_certificate.cer \
	-storepass "${KEYSTORE_PASS}" \
	-noprompt

keytool -import -v \
	-trustcacerts \
	-alias trino_trust \
	-file "${SSL_DIR}"/trino_certificate.cer \
	-keystore "${SSL_DIR}"/truststore.jks \
	-storepass "${TRUSTSTORE_PASS}" \
	-noprompt

echo "Setting up password file..."
sudo yum install httpd-tools -y
htpasswd -cbB -C 10 /usr/lib/trino/etc/password.db alice trinoRocks15
htpasswd -bB -C 10 /usr/lib/trino/etc/password.db bob trinoRocks15
