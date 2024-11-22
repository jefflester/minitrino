# Postgres Catalog Module

This module provisions a standalone Postgres service. By default, it is exposed
both to the internal Docker network and the host via:

```yaml
ports:
  - 5432:5432
```

This will allows users to connect to the service from any SQL client that
supports Postgres drivers on `localhost:5432`.

## Usage

```sh
minitrino -v provision -m postgres
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m postgres

docker exec -it trino bash 
trino-cli

trino> SHOW SCHEMAS FROM postgres;
```
