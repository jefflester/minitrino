#!/usr/bin/env bash

echo "Creating directories..."
PRESTO_CERTS=/usr/lib/presto/etc/certs
if [ ! -d "${PRESTO_CERTS}" ]
then
	mkdir "${PRESTO_CERTS}";
fi

PRESTO_LDAP_USERS=/usr/lib/presto/etc/ldap-users;
if [ ! -d "${PRESTO_LDAP_USERS}" ]
then
	mkdir "${PRESTO_LDAP_USERS}";
fi

echo "Configuring Presto truststore..."
TRUSTSTORE_PATH=/etc/pki/java/cacerts
TRUSTSTORE_PASS=changeit

PRESTO_JAVA_OPTS="${PRESTO_JAVA_OPTS} -Djavax.net.ssl.trustStore=${TRUSTSTORE_PATH}"
PRESTO_JAVA_OPTS="${PRESTO_JAVA_OPTS} -Djavax.net.ssl.trustStorePassword=${TRUSTSTORE_PASS}"

echo "Enabling SSL debug logging..."
PRESTO_JAVA_OPTS="${PRESTO_JAVA_OPTS} -Djavax.net.debug=ssl:handshake:verbose"

echo "Getting LDAP certificate..."
yum install -y openssl &&
LDAP_URI=$(cat /usr/lib/presto/etc/password-authenticator.properties | grep "ldaps" | sed -r "s/^.*ldaps:\/\/(.+:[0-9]+).*$/\1/")
LDAP_HOST=$(echo "${LDAP_URI}" | cut -d ':' -f 1)
LDAP_PORT=$(echo "${LDAP_URI}" | cut -d ':' -f 2)
LDAP_IP=$(ping -c 1 "${LDAP_HOST}" | grep "PING ${LDAP_HOST}" | sed -r "s/^.+\(([0-9]+(\.[0-9]+)+)\).+$/\1/")

if [[ "${LDAP_URI}" != "" ]]
then
	
	LDAP_CERT_FILE="${PRESTO_CERTS}"/ldapserver.crt
	
	echo "LDAP IP Resolver from [${LDAP_URI}] -> [${LDAP_IP}]"
	openssl s_client -showcerts -connect "${LDAP_IP}":"${LDAP_PORT}" > "${LDAP_CERT_FILE}"
	echo "LDAP SSL Certificate downloaded from [${LDAP_IP}:${LDAP_PORT}] and saved in [${LDAP_CERT_FILE}]"
	
fi

echo "Importing external certificates..."
ls "${PRESTO_CERTS}" | while read -r CERT_FILE;
do
	keytool -import \
		-keystore "${TRUSTSTORE_PATH}" \
		-trustcacerts \
		-alias "${CERT_FILE}" \
		-noprompt \
		-storepass "${TRUSTSTORE_PASS}" \
		-file "${CERT_FILE}";
done;

yum install -y openldap-clients &&
ls "${PRESTO_LDAP_USERS}"/*.ldif | while read -r LDIF_FILE;
do
	echo "LDAP Importing user from file [${LDIF_FILE}]"
	export LDAPTLS_REQCERT=never 
	ldapmodify -x -D "cn=admin,dc=example,dc=com" -w ldap -H ldaps://"${LDAP_IP}":"${LDAP_PORT}" -f "${LDIF_FILE}"
	
done;

echo "Starting Presto..."
/usr/lib/presto/bin/launcher run "${PRESTO_JAVA_OPTS}"

tail -F anything