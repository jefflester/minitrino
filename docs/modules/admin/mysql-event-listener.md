# MySQL Event Listener

Add a [MySQL event
listener](https://trino.io/docs/current/admin/event-listeners-mysql.html) to the
cluster.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m mysql-event-listener
```

{{ connect_trino_cli }}

Query is logged to event listener DB:

```sql
SHOW SCHEMAS FROM tpch; 
```

Query the event listener DB:

```sql
SELECT * FROM mysql_event_listener.event_listener.trino_queries;
```
