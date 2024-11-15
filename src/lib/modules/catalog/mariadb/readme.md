# MariaDB Catalog Module

This module provisions a standalone MariaDB service. By default, it is exposed
to the internal Docker network only via:

    ports:
      - :3306

To expose it at the host level, add a port to the left of the colon, e.g.:

    ports:
      - 3307:3306

This will allow you to connect to the service from any SQL client that supports
MariaDB drivers on `localhost:3307`. Note that a unique port (`3307`) was used
here as the MySQL module already claims the host port `3306`.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module mariadb
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from mariadb;
