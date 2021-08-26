# Postgres Connector Module

This module provisions a standalone Postgres service. It is named uniquely to
avoid conflicts with other modules that may use Trino as a backend, such as the
`hive-s3` module.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module postgres
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from postgres;
