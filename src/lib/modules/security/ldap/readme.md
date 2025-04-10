# LDAP Password Authenticator Module

This module provisions an LDAP server for authenticating users in Trino.

## Usage

```sh
minitrino -v provision -m ldap
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m ldap

docker exec -it trino bash 

trino-cli --server https://trino:8443 \
  --truststore-path /etc/starburst/tls-mnt/truststore.jks \
  --truststore-password changeit \
  --user bob --password

trino> SHOW SCHEMAS FROM tpch;
```

## Default Usernames and Passwords

- `admin` / `trinoRocks15`
- `alice` / `trinoRocks15`
- `bob` / `trinoRocks15`

## Add a New User to LDAP

1. Open a shell to the LDAP container

```sh
docker exec -it ldap bash
```

2. Create an LDIF file with the new user information:

```sh
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
```

3. Use the `ldapmodify` tool to add the new user

```sh
ldapmodify -x -D "cn=admin,dc=example,dc=com" \
  -w trinoRocks15 -H ldaps://ldap:636 -f jeff.ldif
```
