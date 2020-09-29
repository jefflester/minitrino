#!/usr/bin/env bash

set -euxo pipefail
export LDAPTLS_REQCERT=never

echo "Waiting for LDAP to come up..."
/opt/minipresto/wait-for-it.sh ldap:636 --strict --timeout=60 -- echo "LDAP service is up."

echo "Creating certs directory..."
PRESTO_CERTS=/usr/lib/presto/etc/certs
if [ ! -d "${PRESTO_CERTS}" ]; then
	mkdir "${PRESTO_CERTS}"
fi

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

echo "Getting LDAP certificate..."
sudo yum install -y openssl
LDAP_URI=$(cat /usr/lib/presto/etc/password-authenticator.properties | grep "ldaps" | sed -r "s/^.*ldaps:\/\/(.+:[0-9]+).*$/\1/")
LDAP_HOST=$(echo "${LDAP_URI}" | cut -d ':' -f 1)
LDAP_PORT=$(echo "${LDAP_URI}" | cut -d ':' -f 2)
LDAP_IP=$(ping -c 1 "${LDAP_HOST}" | grep "PING ${LDAP_HOST}" | sed -r "s/^.+\(([0-9]+(\.[0-9]+)+)\).+$/\1/")

if [[ "${LDAP_URI}" != "" ]]; then
	LDAP_CERT_FILE="${PRESTO_CERTS}"/ldapserver.crt
	echo "LDAP IP resolver from [${LDAP_URI}] -> [${LDAP_IP}]"
	set +e && echo "Q" | openssl s_client -showcerts -connect "${LDAP_IP}:${LDAP_PORT}" > "${LDAP_CERT_FILE}" && set -e
	echo "LDAP SSL certificate downloaded from [${LDAP_IP}:${LDAP_PORT}] and saved in [${LDAP_CERT_FILE}]"
fi

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

echo "Importing external certificates..."
ls "${PRESTO_CERTS}"/* | while read -r CERT_FILE;
do
	sudo keytool -import \
		-keystore "${TRUSTSTORE_PATH}" \
		-trustcacerts \
		-alias "${CERT_FILE}" \
		-noprompt \
		-storepass "${TRUSTSTORE_PASS}" \
		-file "${CERT_FILE}";
done;

sudo yum install -y openldap-clients
ls /usr/lib/presto/etc/ldap-users/*.ldif | while read -r LDIF_FILE;
do
	echo "LDAP Importing user from file [${LDIF_FILE}]"
	ldapmodify -x -D "cn=admin,dc=example,dc=com" -w prestoRocks15 -H ldaps://"${LDAP_IP}":"${LDAP_PORT}" -f "${LDIF_FILE}"
done;

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

echo "Adding truststore in ${SSL_DIR}..."
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
