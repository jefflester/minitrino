# LDAP Module

This module provisions an LDAP server for authenticating users in Trino. This
also enables SSL / TLS between the LDAP server and Trino, and between Trino and
clients. It is compatible with other security modules like **system-ranger** and
**event-logger**, but is mutually-exclusive of the **password-file** module.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module ldap
    docker exec -it trino bash 
    
    trino-cli --server https://trino:8443 \
       --truststore-path /etc/starburst/ssl/truststore.jks --truststore-password trinoRocks15 \
       --keystore-path /etc/starburst/ssl/keystore.jks --keystore-password trinoRocks15 \
       --user bob --password

    trino> show schemas from tpch;

## Default Usernames and Passwords

- alice / trinoRocks15
- bob / trinoRocks15

## Client Keystore and Truststore

The Java keystore and truststore needed for clients and drivers to securely
connect to Trino are located in a volume mount `~/.minitrino/ssl`. These two
files are transient and will be automatically replaced whenever Minitrino is
provisioned with a security module that enables SSL.

## Accessing Trino with the CLI

Via Docker:

    docker exec -it trino trino-cli --server https://trino:8443 \
       --truststore-path /etc/starburst/ssl/truststore.jks --truststore-password trinoRocks15 \
       --keystore-path /etc/starburst/ssl/keystore.jks --keystore-password trinoRocks15 \
       --user bob --password

Via host machine:

    trino-cli-xxx-executable.jar --server https://localhost:8443 \
       --truststore-path ~/.minitrino/ssl/truststore.jks --truststore-password trinoRocks15 \
       --keystore-path ~/.minitrino/ssl/keystore.jks --keystore-password trinoRocks15 \
       --user bob --password

Note that the CLI will prompt you for the password.

## Accessing the Trino Web UI

Open a web browser and go to <https://localhost:8443> and log in with a valid
LDAP username and password.

To have the browser accept the self-signed certificate, do the following:

**Chrome**: Click anywhere on the page and type `thisisunsafe`.

**Firefox**: Click on the **Advanced** button and then click on **Accept the
Risk and Continue**.

**Safari**: Click on the button **Show Details** and then click the link **visit
this website**.

## Adding a New User to LDAP

1. Open a shell to the LDAP container

        docker exec -it ldap bash

2. Create an LDIF file with the new user information:

        cat << EOF > jeff.ldif
        dn: uid=jeff,dc=example,dc=com
        changetype: add
        uid: jeff
        objectClass: inetOrgPerson
        objectClass: organizationalPerson
        objectClass: person
        objectClass: top
        cn: jeff
        sn: jeff
        mail: jeff@example.com
        userPassword: trinoRocks15
        EOF

3. Use the **ldapmodify** tool to add the new user

        ldapmodify -x -D "cn=admin,dc=example,dc=com" \
            -w trinoRocks15 -H ldaps://ldap:636 -f jeff.ldif
