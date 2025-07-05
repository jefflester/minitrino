# Kerberos Authentication

Enable [Kerberos](https://trino.io/docs/current/security/kerberos.html)
authentication on the coordinator.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m kerberos
```

{{ connect_trino_cli }}

Connect to the coordinator using Kerberos authentication:

```sh
kinit -k -t \
  /etc/${CLUSTER_DIST}/krb5/keytabs/admin.keytab \
  admin@MINITRINO.COM

klist

trino-cli \
  --user admin --insecure --debug \
  --server https://minitrino-${CLUSTER_NAME}:8443 \
  --krb5-principal admin@MINITRINO.COM \
  --krb5-config-path /etc/${CLUSTER_DIST}/krb5/krb5.conf \
  --krb5-keytab-path /etc/${CLUSTER_DIST}/krb5/keytabs/admin.keytab \
  --krb5-remote-service-name HTTP
```

Confirm authentication succeeded:

```sql
SELECT current_user;
```

This should return the user:

```text
 admin
```

The pattern can be used for any of the Kerberos principals defined in the table
below.

```sh
kinit -k -t \
  /etc/${CLUSTER_DIST}/krb5/keytabs/${USER}.keytab \
  ${USER}@MINITRINO.COM

klist

trino-cli \
  --user ${USER} --insecure --debug \
  --server https://minitrino-${CLUSTER_NAME}:8443 \
  --krb5-principal ${USER}@MINITRINO.COM \
  --krb5-config-path /etc/${CLUSTER_DIST}/krb5/krb5.conf \
  --krb5-keytab-path /etc/${CLUSTER_DIST}/krb5/keytabs/${USER}.keytab \
  --krb5-remote-service-name HTTP
```

## Valid Kerberos Principals

```{table}
| Principal | Keytab |
|:-----------------|:---------------|
| `admin@MINITRINO.COM` | `/etc/${CLUSTER_DIST}/krb5/keytabs/admin.keytab` |
| `cachesvc@MINITRINO.COM` | `/etc/${CLUSTER_DIST}/krb5/keytabs/cachesvc.keytab` |
| `bob@MINITRINO.COM` | `/etc/${CLUSTER_DIST}/krb5/keytabs/bob.keytab` |
| `alice@MINITRINO.COM` | `/etc/${CLUSTER_DIST}/krb5/keytabs/alice.keytab` |
| `metadata-user@MINITRINO.COM` | `/etc/${CLUSTER_DIST}/krb5/keytabs/metadata-user.keytab` |
| `platform-user@MINITRINO.COM` | `/etc/${CLUSTER_DIST}/krb5/keytabs/platform-user.keytab` |
| `test@MINITRINO.COM` | `/etc/${CLUSTER_DIST}/krb5/keytabs/test.keytab` |
```

## User Mapping

The Kerberos principal is mapped to the Trino user via the
`http-server.authentication.krb5.user-mapping.pattern` configuration property.
This ensures that the "normal" username resolves to ensure proper integration
with other modules, e.g. group providers and access control modules.

```{table}
| Principal | User |
|:-----------------|:---------------|
| `admin@MINITRINO.COM` | `admin` |
| `cachesvc@MINITRINO.COM` | `cachesvc` |
| `bob@MINITRINO.COM` | `bob` |
| `alice@MINITRINO.COM` | `alice` |
| `metadata-user@MINITRINO.COM` | `metadata-user` |
| `platform-user@MINITRINO.COM` | `platform-user` |
| `test@MINITRINO.COM` | `test` |
```

## Dependent Modules

- [`tls`](tls.md#tls): Required for securing credentials in transit.
