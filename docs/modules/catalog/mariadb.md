# MariaDB Catalog

Add a [MariaDB catalog](https://trino.io/docs/current/connector/mariadb.html) to
the cluster along with a standalone MariaDB service.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m mariadb
```

{{ connect_trino_cli }}

Confirm MariaDB is reachable:

```sql
SHOW SCHEMAS FROM mariadb;
```
