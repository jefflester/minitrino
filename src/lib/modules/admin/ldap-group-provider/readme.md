# LDAP Group Provider Module

Enable user-group mapping using the [LDAP group
provider](https://docs.starburst.io/latest/security/ldap-group-provider.html).

-----

***This module requires a Starburst distribution and license.***

-----

## Usage

```sh
minitrino provision -i starburst -m ldap-group-provider
minitrino exec -i 'trino-cli --user admin'
```

Display the groups for the current user via `current_groups()`:

```sql
SELECT current_groups();
-- [clusteradmins]
```

The group provider maps groups to users regardless of authentication.

```sh
minitrino exec -i 'trino-cli --user test'
```

```sql
SELECT current_groups();
-- [clusteradmins, metadata-users, platform-users] 
```

```sh
minitrino exec -i
trino-cli --server https://minitrino-${CLUSTER_NAME}:8443 \
  --insecure --user admin --password
```

```sql
SELECT current_groups();
-- [clusteradmins]
```

## Group Mapping

| Group              | Users                            |
|:-------------------|:---------------------------------|
| `clusteradmins`    | `admin`, `cachesvc`, `test`      |
| `metadata-users`   | `metadata-user`, `bob`, `test`   |
| `platform-users`   | `platform-user`, `alice`, `test` |

## Dependent Modules

- `ldap`: Required for LDAP users/groups.
