# Password File Authentication Module
This module configures Presto to authenticate users with a password file. It
also enables SSL / TLS between Presto and clients. It is compatible with other
security modules like **system-ranger** and **event-logger**, but is
mutually-exclusive of the **ldap** module.

## Requirements
- N/A

## Sample Usage
To provision this module, run:

```shell
minipresto provision --security ldap
```

## Default Usernames and Passwords
- alice / prestoRocks15
- bob / prestoRocks15

## Client Keystore and Truststore
The Java keystore and truststore needed for clients and drivers to securely
connect to Presto are located in a volume mount `~/.minipresto/ssl`. These two
files are transient and will be automatically replaced whenever Minipresto is
provisioned with a security module that enables SSL.

## Accessing Presto with the CLI

Via Docker:

```
docker exec -it presto presto-cli --server https://presto:8443 \
   --truststore-path /usr/lib/presto/etc/ssl/truststore.jks --truststore-password prestoRocks15 \
   --keystore-path /usr/lib/presto/etc/ssl/keystore.jks --keystore-password prestoRocks15 \
   --user bob --password
```

Via Host Machine:

```
presto-cli-xxx-executable.jar --server https://localhost:8443 \
   --truststore-path ~/.minipresto/ssl/truststore.jks --truststore-password prestoRocks15 \
   --keystore-path ~/.minipresto/ssl/keystore.jks --keystore-password prestoRocks15 \
   --user bob --password
```

Note that the CLI will prompt you for the password.

## Accessing the Presto Web UI
Open a web browser and go to https://localhost:8443 and log in with a valid
username and password.

To have the browser accept the self-signed certificate, do the following:

**Chrome**: Click anywhere on the page and type `thisisunsafe`.

**Firefox**: Click on the **Advanced** button and then click on **Accept the
Risk and Continue**.

**Safari**: Click on the button **Show Details** and then click the link **visit
this website**.

## Adding a New User to the Password File

Example with username `jeff` and password `prestoRocks15`

```
docker exec presto htpasswd -bB -C 10 /usr/lib/presto/etc/password.db jeff prestoRocks15
```
