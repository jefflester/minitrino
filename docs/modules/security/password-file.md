# Password File Authentication

Enable
[password file authentication](https://trino.io/docs/current/security/password-file.html)
on the coordinator.

## Usage

Provision the module:

```sh
minitrino provision -m password-file
```

{{ coordinator_shell }}

Authenticate to the coordinator using the Trino CLI:

```sh
trino-cli --server https://minitrino:8443 \
  --truststore-path /etc/"${CLUSTER_DIST}"/tls/truststore.jks \
  --truststore-password changeit \
  --user bob --password
```

Confirm authentication by running a query:

```sql
SHOW SCHEMAS FROM tpch;
```

Access the web UI at `https://localhost:8443` and authenticate with one of the
sets of credentials listed below.

## Default Usernames and Passwords

```{table}
| Username | Password |
|:-----------------|:---------------|
| `admin` | `trinoRocks15` |
| `cachesvc` | `trinoRocks15` |
| `bob` | `trinoRocks15` |
| `alice` | `trinoRocks15` |
| `metadata-user` | `trinoRocks15` |
| `platform-user` | `trinoRocks15` |
| `test` | `trinoRocks15` |
```

## Add a New User Credential

{{ coordinator_shell }}

Add a new user to the password file using `htpasswd`:

```sh
htpasswd -bB -C 10 /etc/${CLUSTER_DIST}/password.db <user> <pass>
```

## Remove or Update a User

To remove a user:

```sh
htpasswd -D /etc/${CLUSTER_DIST}/password.db <user>
```

To update a user's password, simply re-run the add command with the new
password:

```sh
htpasswd -bB -C 10 /etc/${CLUSTER_DIST}/password.db <user> <pass>
```

## Dependent Modules

- [`tls`](tls.md#tls): Required for securing credentials in transit.
