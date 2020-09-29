#!/usr/bin/env bash

set -euxo pipefail

echo "Setting variables..."
TRUSTSTORE_PATH=/etc/pki/java/cacerts
TRUSTSTORE_DEFAULT_PASS=changeit
TRUSTSTORE_PASS=prestoRocks15
KEYSTORE_PASS=prestoRocks15
SSL_DIR=/usr/lib/presto/etc/ssl

PRESTO_JAVA_OPTS="-Djavax.net.ssl.trustStore=${TRUSTSTORE_PATH} \n"
PRESTO_JAVA_OPTS="${PRESTO_JAVA_OPTS}-Djavax.net.ssl.trustStorePassword=${TRUSTSTORE_PASS} \n"
PRESTO_JAVA_OPTS="${PRESTO_JAVA_OPTS}-Djavax.net.debug=ssl:handshake:verbose \n"

echo "Removing pre-existing SSL resources..."
# These should be removed prior to provisioning to ensure they do not conflate
# with other SSL resources
rm -f "${SSL_DIR}"/* 
echo "Generating keystore file..."
keytool -genkeypair \
	-alias presto \
	-keyalg RSA \
	-keystore "${SSL_DIR}"/keystore.jks \
	-keypass "${KEYSTORE_PASS}" \
	-storepass "${KEYSTORE_PASS}" \
	-dname "CN=*.starburstdata.com" \
	-ext san=dns:presto.minipresto.starburstdata.com,dns:presto,dns:localhost

echo "Change truststore password..."
keytool -storepasswd \
        -storepass "${TRUSTSTORE_DEFAULT_PASS}" \
        -new "${TRUSTSTORE_PASS}" \
        -keystore "${TRUSTSTORE_PATH}"

echo "Adding JVM configs..."
echo -e "${PRESTO_JAVA_OPTS}" >> /usr/lib/presto/etc/jvm.config

echo "Adding Presto configs..."
cat <<EOT >> /usr/lib/presto/etc/config.properties
http-server.authentication.type=PASSWORD
http-server.https.enabled=true
http-server.https.port=8443
http-server.https.keystore.path=/usr/lib/presto/etc/ssl/keystore.jks
http-server.https.keystore.key=prestoRocks15
EOT

echo "Adding keystore and truststore in ${SSL_DIR}..."
keytool -export \
	-alias presto \
	-keystore "${SSL_DIR}"/keystore.jks \
	-rfc \
	-file "${SSL_DIR}"/presto_certificate.cer \
	-storepass "${KEYSTORE_PASS}" \
	-noprompt

keytool -import -v \
	-trustcacerts \
	-alias presto_trust \
	-file "${SSL_DIR}"/presto_certificate.cer \
	-keystore "${SSL_DIR}"/truststore.jks \
	-storepass "${TRUSTSTORE_PASS}" \
	-noprompt

echo "Setting up password file..."
sudo yum install httpd-tools -y
htpasswd -cbB -C 10 /usr/lib/presto/etc/password.db alice prestoRocks15
htpasswd -bB -C 10 /usr/lib/presto/etc/password.db bob prestoRocks15
