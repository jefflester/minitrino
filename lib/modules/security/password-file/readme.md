# Password File Authentication Module
This module configures Presto to authenticate users with a password file. It also enables SSL / TLS between Presto and clients. It is compatible with other security modules like **system-ranger** and **event-logger**, but is mutually-exclusive of the **ldap** module.

## Requirements
- N/A

## Sample Usage
To provision this module, run:

```shell
minipresto provision --security password-file
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
docker exec -it presto /usr/lib/presto/lib/presto-cli --server https://presto:8443 \
   --truststore-path /home/presto/truststore.jks --truststore-password prestoRocks15 \
   --keystore-path /home/presto/keystore.jks --keystore-password prestoRocks15 \
   --user bob --password
```

Via Host Machine
```
cd <MINIPRESTO LIB PATH>
presto-cli-xxx-executable.jar --server https://localhost:8443 \
   --truststore-path ssl/truststore.jks --truststore-password prestoRocks15 \
   --keystore-path ssl/keystore.jks --keystore-password prestoRocks15 \
   --user bob --password
```

Note that the CLI will prompt you for the password.

## Accessing the Presto Web UI
Open a web browser and go to https://localhost:8443 and log in with a valid username and password.

To have the browser accept the self-signed certificate, do the following:

**Chrome**: Click anywhere on the page and type `thisisunsafe`.

**Firefox**: Click on the **Advanced** button and then click on **Accept the Risk and Continue**.

**Safari**: Click on the button **Show Details** and then click the link **visit this website**.

## Adding a new user to the password file

Example with username `jeff` and password `prestoRocks15`
```
docker exec presto htpasswd -bB -C 10 /usr/lib/presto/etc/password.db jeff prestoRocks15
```
