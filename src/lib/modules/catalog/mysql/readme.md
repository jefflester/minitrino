# MySQL Connector Module

This module provisions a standalone MySQL service. Other modules that uses MySQL
as a backend will need a more unique name to avoid conflicts with this one.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module mysql
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from mysql;
