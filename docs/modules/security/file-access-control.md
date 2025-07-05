# File-Based Access Control

Enable [file-based access
control](https://trino.io/docs/current/security/file-system-access-control.html).

## Usage

Provision the module:

```sh
minitrino provision -m file-access-control
```

Connect to the coordinator container's Trino CLI:

```sh
minitrino exec -i 'trino-cli --user admin'
```

Confirm catalog visibility:

```sql
SHOW CATALOGS;
```

```text
 Catalog 
---------
 jmx     
 memory  
 system  
 tpcds   
 tpch
```

Switch to a non-admin user:

```sh
minitrino exec -i 'trino-cli --user alice'
```

Confirm catalog visibility:

```sql
SHOW CATALOGS;
```

```text
 Catalog 
---------
 system 
```

## Access Control Rules

The access control rules are located in the `rules.json` file which defines
groups of users that map to certain access control permissions. The users for
the groups are defined in the `groups.txt` file (See the
[`file-group-provider`](../admin/file-group-provider.md#file-group-provider)
module for more information).

```{table}
| Group              | Access |
|:-------------------|:---------------------------------|
| `clusteradmins` | Full access to all objects in the cluster |
| `metadata-users` | Access to the tables within the `system.metadata`, `system.jdbc`, and `system.information_schema` schemas |
| `platform-users` | Access to the tables within the `system.runtime` schema |
```

## Dependent Modules

- [`file-group-provider`](../admin/file-group-provider.md#file-group-provider):
  Maps users to groups using a mapping file.
