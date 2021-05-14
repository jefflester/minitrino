# Password File Authentication Module
This module configures Trino to authenticate users with a password file. It
also enables SSL / TLS between Trino and clients. It is compatible with other
security modules like **system-ranger** and **event-logger**, but is
mutually-exclusive of the **ldap** module.

## Requirements
- N/A

## Sample Usage
To provision this module, run:

```shell
minitrino provision --module ldap
```

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

```
docker exec -it trino trino-cli --server https://trino:8443 \
   --truststore-path /etc/starburst/ssl/truststore.jks --truststore-password trinoRocks15 \
   --keystore-path /etc/starburst/ssl/keystore.jks --keystore-password trinoRocks15 \
   --user bob --password
```

Via Host Machine:

```
trino-cli-xxx-executable.jar --server https://localhost:8443 \
   --truststore-path ~/.minitrino/ssl/truststore.jks --truststore-password trinoRocks15 \
   --keystore-path ~/.minitrino/ssl/keystore.jks --keystore-password trinoRocks15 \
   --user bob --password
```

Note that the CLI will prompt you for the password.

## Accessing the Trino Web UI
Open a web browser and go to https://localhost:8443 and log in with a valid
username and password.

To have the browser accept the self-signed certificate, do the following:

**Chrome**: Click anywhere on the page and type `thisisunsafe`.

**Firefox**: Click on the **Advanced** button and then click on **Accept the
Risk and Continue**.

**Safari**: Click on the button **Show Details** and then click the link **visit
this website**.

## Adding a New User to the Password File

Example with username `jeff` and password `trinoRocks15`

```
docker exec trino htpasswd -bB -C 10 /etc/starburst/password.db jeff trinoRocks15
```
