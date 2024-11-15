# SQL Server Catalog Module

This module provisions a standalone SQL Server service. By default, it is
exposed both to the internal Docker network and the host via:

    ports:
      - 1433:1433

This will allows users to connect to the service from any SQL client that
supports SQL Server drivers on `localhost:1433`.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module sqlserver
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from sqlserver;
