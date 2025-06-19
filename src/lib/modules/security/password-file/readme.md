# Password File Authenticator Module

This module configures [password file
authentication](https://trino.io/docs/current/security/password-file.html).

## Usage

```sh
minitrino -v provision -m password-file
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m password-file

docker exec -it minitrino bash 

trino-cli --server https://minitrino:8443 \
  --truststore-path /etc/"${CLUSTER_DIST}"/tls/truststore.jks --truststore-password changeit \
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
docker exec minitrino htpasswd -bB -C 10 /etc/${CLUSTER_DIST}/password.db admin trinoRocks15
```
