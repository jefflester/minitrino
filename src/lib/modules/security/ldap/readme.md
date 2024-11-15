# LDAP Password Authenticator Module

This module provisions an LDAP server for authenticating users in Trino.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module ldap
    docker exec -it trino bash 
    
    trino-cli --server https://trino:8443 \
       --truststore-path /etc/starburst/tls-mnt/truststore.jks --truststore-password changeit \
       --user bob --password

    trino> show schemas from tpch;

## Default Usernames and Passwords

- admin / trinoRocks15
- alice / trinoRocks15
- bob / trinoRocks15

## Add a New User to LDAP

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

3. Use the `ldapmodify` tool to add the new user

        ldapmodify -x -D "cn=admin,dc=example,dc=com" \
            -w trinoRocks15 -H ldaps://ldap:636 -f jeff.ldif
