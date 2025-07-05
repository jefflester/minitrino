# File Group Provider

Enable user-group mapping using the [file-based group
provider](https://trino.io/docs/current/security/group-file.html).

## Usage

Provision the module:

```sh
minitrino provision -m file-group-provider
```

{{ connect_trino_cli_admin }}

Display the groups for the current user via `current_groups()`:

```sql
SELECT current_groups();
-- [clusteradmins]
```

View the groups for the `test` user:

```sh
minitrino exec -i 'trino-cli --user test'
```

```sql
SELECT current_groups();
-- [clusteradmins, metadata-users, platform-users]
```

## Group Mapping

| Group | Users |
|:-------------------|:---------------------------------|
| `clusteradmins` | `admin`, `cachesvc`, `test` |
| `metadata-users` | `metadata-user`, `bob`, `test` |
| `platform-users` | `platform-user`, `alice`, `test` |
