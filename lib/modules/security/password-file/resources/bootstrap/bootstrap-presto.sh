#!/usr/bin/env bash

set -euxo pipefail

echo "Configuring Presto truststore..."
TRUSTSTORE_PATH=/etc/pki/java/cacerts
TRUSTSTORE_DEFAULT_PASS=changeit
TRUSTSTORE_PASS=prestoRocks15

PRESTO_JAVA_OPTS="-Djavax.net.ssl.trustStore=${TRUSTSTORE_PATH} \n"
PRESTO_JAVA_OPTS="${PRESTO_JAVA_OPTS}-Djavax.net.ssl.trustStorePassword=${TRUSTSTORE_PASS} \n"
PRESTO_JAVA_OPTS="${PRESTO_JAVA_OPTS}-Djavax.net.debug=ssl:handshake:verbose \n"

echo "Generating keystore file..."
keytool -genkeypair \
	-alias presto \
	-keyalg RSA \
	-keystore /usr/lib/presto/etc/keystore.jks \
	-keypass prestoRocks15 \
	-storepass prestoRocks15 \
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
http-server.https.keystore.path=/usr/lib/presto/etc/keystore.jks
http-server.https.keystore.key=prestoRocks15
EOT

echo "Adding keystore and truststore in /home/presto..."
rm -f /home/presto/keystore.jks
rm -f /home/presto/truststore.jks
cp /usr/lib/presto/etc/keystore.jks /home/presto/keystore.jks
keytool -export -alias presto -keystore /home/presto/keystore.jks -rfc -file /home/presto/presto_certificate.cer -storepass prestoRocks15 -noprompt
keytool -import -v -trustcacerts -alias presto_trust -file /home/presto/presto_certificate.cer -keystore /home/presto/truststore.jks -storepass prestoRocks15 -noprompt
rm /home/presto/presto_certificate.cer

echo "Setting up password file"
sudo yum install httpd-tools -y
htpasswd -cbB -C 10 /usr/lib/presto/etc/password.db alice prestoRocks15
htpasswd -bB -C 10 /usr/lib/presto/etc/password.db bob prestoRocks15
