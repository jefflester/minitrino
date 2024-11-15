# Postgres Catalog Module

This module provisions a standalone Postgres service. By default, it is exposed
both to the internal Docker network and the host via:

    ports:
      - 5432:5432

This will allows users to connect to the service from any SQL client that
supports Postgres drivers on `localhost:5432`.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module postgres
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from postgres;
