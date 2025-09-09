# LDAP Group Provider

Enable user-group mapping using the
[LDAP group provider](https://docs.starburst.io/latest/security/ldap-group-provider.html).

## Usage

{{ starburst_license_warning }}

Provision the module:

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m ldap-group-provider
```

{{ connect_trino_cli_admin }}

Display the groups for the current user via `current_groups()`:

```sql
SELECT current_groups();
-- [clusteradmins]
```

The group provider maps groups to users regardless of authentication.

Without auth:

```sh
minitrino exec -i 'trino-cli --user test'
```

```sql
SELECT current_groups();
-- [clusteradmins, metadata-users, platform-users]
```

With auth:

```sh
minitrino exec -i \
    'trino-cli --server https://minitrino:8443 \
    --insecure --user admin --password'
```

```sql
SELECT current_groups();
-- [clusteradmins]
```

## Group Mapping

| Group            | Users                            |
| :--------------- | :------------------------------- |
| `clusteradmins`  | `admin`, `cachesvc`, `test`      |
| `metadata-users` | `metadata-user`, `bob`, `test`   |
| `platform-users` | `platform-user`, `alice`, `test` |

## Dependent Modules

- [`ldap`](../security/ldap.md#ldap-authentication): Required for LDAP
  users/groups.
