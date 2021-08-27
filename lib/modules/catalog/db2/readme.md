# Db2 Connector Module

This module provisions a standalone Db2 service.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module db2
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from db2;
