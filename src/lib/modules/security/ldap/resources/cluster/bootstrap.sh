#!/usr/bin/env bash

set -euxo pipefail

before_start() {
	export LDAPTLS_REQCERT=never

	echo "Waiting for LDAP to come up..."
	wait-for-it ldap:636 --strict --timeout=60 -- echo "LDAP service is up."

	echo "Getting LDAP certificate..."
	LDAP_URI=$(grep "ldaps" /etc/"${CLUSTER_DIST}"/password-authenticator.properties | sed -r "s/^.*ldaps:\/\/(.+:[0-9]+).*$/\1/")
	LDAP_HOST=$(echo "${LDAP_URI}" | cut -d ':' -f 1)
	LDAP_PORT=$(echo "${LDAP_URI}" | cut -d ':' -f 2)
	LDAP_IP=$(ping -c 1 "${LDAP_HOST}" | grep "PING ${LDAP_HOST}" | sed -r "s/^.+\(([0-9]+(\.[0-9]+)+)\).+$/\1/")

	LDAP_CERTS=/tmp/ldap-tls/
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
	find "${LDAP_CERTS}" -type f | while read -r CERT_FILE;
	do
		local alias="${CERT_FILE}"
		if keytool -list -keystore /etc/"${CLUSTER_DIST}"/tls-jvm/cacerts \
		    -storepass changeit -alias "${alias}" > /dev/null 2>&1; then
			echo "Alias ${alias} already exists, skipping import."
		else
			keytool -import -v \
				-trustcacerts \
				-alias "${alias}" \
				-file "${CERT_FILE}" \
				-keystore /etc/"${CLUSTER_DIST}"/tls-jvm/cacerts \
				-storepass changeit \
				-noprompt
		fi
	done

	find /etc/"${CLUSTER_DIST}"/ldif/ -type f -name "*.ldif" | while read -r LDIF_FILE;
	do
		echo "Importing LDAP object from file [${LDIF_FILE}]"
		set +e
		ldapadd -x \
			-D "cn=admin,dc=minitrino,dc=com" \
			-w trinoRocks15 \
			-H ldaps://"${LDAP_IP}":"${LDAP_PORT}" \
			-f "${LDIF_FILE}"
		rc=$?
		set -e
		if [ "$rc" -eq 68 ]; then
			echo "LDAP object already exists, skipping."
		elif [ "$rc" -ne 0 ]; then
			echo "ldapadd failed with code $rc"
			exit $rc
		fi
	done
}

after_start() {
	:
}
