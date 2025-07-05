# Postgres Catalog

Add a
[Postgres catalog](https://trino.io/docs/current/connector/postgresql.html) to
the cluster along with a standalone Postgres service.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m postgres
```

{{ connect_trino_cli }}

Confirm Postgres is reachable:

```sql
SHOW SCHEMAS FROM postgres;
```
