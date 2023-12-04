#!/usr/bin/env bash

set -euxo pipefail
export LDAPTLS_REQCERT=never

echo "Waiting for LDAP to come up..."
wait-for-it ldap:636 --strict --timeout=60 -- echo "LDAP service is up."

echo "Getting LDAP certificate..."
LDAP_URI=$(cat /etc/starburst/password-authenticator.properties | grep "ldaps" | sed -r "s/^.*ldaps:\/\/(.+:[0-9]+).*$/\1/")
LDAP_HOST=$(echo "${LDAP_URI}" | cut -d ':' -f 1)
LDAP_PORT=$(echo "${LDAP_URI}" | cut -d ':' -f 2)
LDAP_IP=$(ping -c 1 "${LDAP_HOST}" | grep "PING ${LDAP_HOST}" | sed -r "s/^.+\(([0-9]+(\.[0-9]+)+)\).+$/\1/")

LDAP_CERTS=/etc/starburst/ssl/ldap/
if [ ! -d "${LDAP_CERTS}" ]; then
	mkdir -p "${LDAP_CERTS}"
fi

if [[ "${LDAP_URI}" != "" ]]; then
	LDAP_CERT_FILE="${LDAP_CERTS}"/ldapserver.crt
	echo "LDAP IP resolver from [${LDAP_URI}] -> [${LDAP_IP}]"
	set +e && echo "Q" | openssl s_client -showcerts -connect "${LDAP_IP}:${LDAP_PORT}" > "${LDAP_CERT_FILE}" && set -e
	echo "LDAP SSL certificate downloaded from [${LDAP_IP}:${LDAP_PORT}] and saved in [${LDAP_CERT_FILE}]"
fi

echo "Importing LDAP certificates..."
ls "${LDAP_CERTS}"/* | while read -r CERT_FILE;
do
	keytool -import -v \
		-trustcacerts \
		-alias "${CERT_FILE}" \
		-file "${CERT_FILE}" \
		-keystore /etc/ssl/certs/java/cacerts \
		-storepass changeit \
		-noprompt;
done;

ls /etc/starburst/ldap-users/*.ldif | while read -r LDIF_FILE;
do
	echo "LDAP Importing user from file [${LDIF_FILE}]"
	ldapmodify -x -D "cn=admin,dc=example,dc=com" -w trinoRocks15 -H ldaps://"${LDAP_IP}":"${LDAP_PORT}" -f "${LDIF_FILE}"
done;
