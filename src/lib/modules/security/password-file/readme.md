# Password File Authenticator Module

This module configures Trino to authenticate users with a password file.

## Usage

```sh
minitrino -v provision -m password-file
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m password-file

docker exec -it trino bash 

trino-cli --server https://trino:8443 \
  --truststore-path /etc/starburst/tls-mnt/truststore.jks --truststore-password changeit \
  --user bob --password
    
trino> SHOW SCHEMAS FROM tpch;
```

## Default Usernames and Passwords

- `admin` / `trinoRocks15`
- `alice` / `trinoRocks15`
- `bob` / `trinoRocks15`

## Adding a New User to the Password File

Example with username `admin` and password `trinoRocks15`

```sh
docker exec trino htpasswd -bB -C 10 /etc/starburst/password.db admin trinoRocks15
```
