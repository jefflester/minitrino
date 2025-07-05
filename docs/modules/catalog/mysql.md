# MySQL Catalog

Add a [MySQL catalog](https://trino.io/docs/current/connector/mysql.html) to the
cluster along with a standalone MySQL service.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m mysql
```

{{ connect_trino_cli }}

Confirm MySQL is reachable:

```sql
SHOW SCHEMAS FROM mysql;
```
