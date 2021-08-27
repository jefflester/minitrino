# SQL Server Connector Module

This module provisions a standalone SQL Server service.

Default database created is `master`.

Note that the 2017 version of SQL Server is used by default, as previous
versions were only available on Windows and do not have Docker containers.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module sqlserver
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from sqlserver;
