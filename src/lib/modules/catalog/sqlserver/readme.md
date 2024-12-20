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

## Persistent Storage

This module uses named volumes to persist SQL Server data:

```yaml
volumes:
  sqlserver-data:
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.sqlserver=catalog-sqlserver
```

The user-facing implication is that SQL Server data is retained even after
shutting down and/or removing the environment's containers. Minitrino issues a
warning about this whenever a module with named volumes is deployed––be sure to
look out for these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label com.starburst.tests.module.sqlserver=catalog-sqlserver
```
  
Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_sqlserver-data
```
