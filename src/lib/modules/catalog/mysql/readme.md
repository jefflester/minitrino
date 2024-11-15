# MySQL Catalog Module

This module provisions a standalone MySQL service. By default, it is exposed
both to the internal Docker network and the host via:

    ports:
      - 3306:3306

This will allows users to connect to the service from any SQL client that
supports MySQL drivers on `localhost:3306`.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module mysql
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from mysql;
