# MySQL Event Listener Module

A module which utilizes Trino's [MySQL event
listener](https://trino.io/docs/current/admin/event-listeners-mysql.html).

The MySQL event listener database is exposed to `localhost` on port `3308`.

Additionally, the MySQL database used for the event listener's storage is
exposed via the `mysql_event_listener` catalog, which can be queried directly
through Trino.

## Usage

```sh
minitrino -v provision -m mysql-event-listener
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m mysql-event-listener

docker exec -it minitrino bash 
trino-cli

# Query is logged to event listener DB
trino> SHOW SCHEMAS FROM tpch; 
# Query the event listener DB
trino> SELECT * FROM mysql_event_listener.event_listener.trino_queries;
```
