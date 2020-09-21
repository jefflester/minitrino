# LDAP Module
This module provisions an LDAP server for authenticating users in Presto. This also enables SSL / TLS between the LDAP server and Presto, and between Presto and clients. It is compatible with other security modules like **system-ranger** and **event-logger**, but is mutually-exclusive of the **password-file** module.

## Requirements
- N/A

## Sample Usage
To provision this module, run:

```shell
minipresto provision --security ldap
```

## Default usernames and passwords
- alice / prestoRocks15
- bob / prestoRocks15

## Client keystore and truststore
The Java keystore and truststore needed for clients and drivers to securely connect to Presto are located in a volume mount `<MINIPRESTO LIB PATH>/ssl`. These two files are transient and will be automatically replaced whenever Minipresto is provisioned with a security module that enables SSL.

## Accessing Presto with the CLI

### Examples
Via Docker

```
docker exec -it presto /usr/lib/presto/lib/presto-cli --server https://presto:8443 --truststore-path /home/presto/truststore.jks --truststore-password prestoRocks15 --keystore-path /home/presto/keystore.jks --keystore-password prestoRocks15 --user bob --password
```

Via Host
```
cd <MINIPRESTO LIB PATH>
presto-cli-xxx-executable.jar --server https://localhost:8443 --truststore-path ssl/truststore.jks --truststore-password prestoRocks15 --keystore-path ssl/keystore.jks --keystore-password prestoRocks15 --user bob --password
```

Note that the CLI will prompt you for the password.

## Accessing the Presto Web UI
Open a web browser and go to https://localhost:8443 and log in with a valid LDAP username and password.

To have the browser accept the self-signed certificate, do the following:

Chrome: Click anywhere on the page and type `thisisunsafe`.
Firefox: Click on the **Advanced** button and then click on **Accept the Risk and Continue**.
Safari: Click on the button **Show Details** and then click the link **visit this website**.

## Adding a new user to LDAP
1. Open a shell to the LDAP container
```
docker exec -it ldap bash
```

2. Create an LDIF file with the new user information:
```
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
userPassword: prestoRocks15
EOF
```

3. Use the **ldapmodify** tool to add the new user
```
ldapmodify -x -D "cn=admin,dc=example,dc=com" -w prestoRocks15 -H ldaps://ldap:636 -f jeff.ldif
```
