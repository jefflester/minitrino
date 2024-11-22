# SQL Server Catalog Module

This module provisions a standalone SQL Server service. By default, it is
exposed both to the internal Docker network and the host via:

```yaml
ports:
  - 1433:1433
```

This will allows users to connect to the service from any SQL client that
supports SQL Server drivers on `localhost:1433`.

## Usage

```sh
minitrino -v provision -m sqlserver
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m sqlserver

docker exec -it trino bash 
trino-cli

trino> SHOW SCHEMAS FROM sqlserver;
```
