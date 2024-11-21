# MySQL Event Listener Module

A module which utilizes Trino's [MySQL event
listener](https://trino.io/docs/current/admin/event-listeners-mysql.html).

The MySQL event listener database is exposed to `localhost` on port `3308`.

Additionally, the MySQL database used for the event listener's storage is
exposed via the `mysql_event_listener` catalog, which can be queried directly
through Trino.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module mysql-event-listener
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from tpch; # Query is logged to event listener DB

    # Query the event listener DB
    trino> select * from mysql_event_listener.event_listener.trino_queries;
