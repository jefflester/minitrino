# LDAP Group Provider Module

Enable user-group mapping using the [LDAP group
provider](https://docs.starburst.io/latest/security/ldap-group-provider.html).

______________________________________________________________________

***This module requires a Starburst distribution and license.***

______________________________________________________________________

## Usage

Provision the module:

```sh
minitrino provision -i starburst -m ldap-group-provider
```

Connect to the `trino-cli` in the coordinator:

```sh
minitrino exec -i 'trino-cli --user admin'
```

Display the groups for the current user via `current_groups()`:

```sql
SELECT current_groups();
-- [clusteradmins]
```

The group provider maps groups to users regardless of authentication.

```sh
# No authentication
minitrino exec -i 'trino-cli --user test'
```

```sql
SELECT current_groups();
-- [clusteradmins, metadata-users, platform-users] 
```

```sh
# Authentication
minitrino exec -i
trino-cli --server https://minitrino:8443 \
  --insecure --user admin --password
```

```sql
SELECT current_groups();
-- [clusteradmins]
```

## Group Mapping

| Group | Users |
|:-------------------|:---------------------------------|
| `clusteradmins` | `admin`, `cachesvc`, `test` |
| `metadata-users` | `metadata-user`, `bob`, `test` |
| `platform-users` | `platform-user`, `alice`, `test` |

## Dependent Modules

- [`ldap`](../../security/ldap/readme.md): Required for LDAP users/groups.
