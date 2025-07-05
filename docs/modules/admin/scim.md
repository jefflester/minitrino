# SCIM

Adds [SCIM](https://docs.starburst.io/latest/security/scim-provisioning.html)
user and group synchronization to the cluster.

## Usage

{{ starburst_license_warning }}

Provision the module:

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m scim
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

## SCIM Sync Client

This module includes a custom Python sync client (`scim_sync.py`) that
automatically provisions and synchronizes users and groups to the Starburst SCIM
API.

The client runs continuously in the background, ensuring the group/user mapping
is always up to date. By default, the mapping is:

| Group | Users |
|------------------|-------------------------------|
| clusteradmins | admin, cachesvc, test |
| metadata-users | metadata-user, bob, test |
| platform-users | platform-user, alice, test |

The sync client is configured via the following environment variables:

- `CLUSTER_NAME`: The cluster name (used to construct the SCIM API URL)
- `SCIM_TOKEN`: Bearer token for SCIM API authentication (default: `changeme`)
- `SYNC_INTERVAL`: How often to sync (seconds, default: 60)

To customize the mapping, edit the `GROUP_MAPPING` dictionary in
`resources/scim/scim_sync.py`.

## Dependent Modules

- [`biac`](../security/biac.md#built-in-access-control): Access control is a
  requirement for the SCIM plugin.
