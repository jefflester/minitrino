# SQL Server Catalog

Add a
[SQL Server catalog](https://trino.io/docs/current/connector/sqlserver.html) to
the cluster along with a standalone SQL Server service.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m sqlserver
```

{{ connect_trino_cli }}

Confirm SQL Server is reachable:

```sql
SHOW SCHEMAS FROM sqlserver;
```
