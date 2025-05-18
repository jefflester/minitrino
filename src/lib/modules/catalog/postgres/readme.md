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
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m postgres

docker exec -it minitrino bash 
trino-cli

trino> SHOW SCHEMAS FROM postgres;
```

## Persistent Storage

This module uses named volumes to persist Postgres data:

```yaml
volumes:
  postgres-data:
    labels:
      - org.minitrino=root
      - org.minitrino.module=catalog-postgres
```

The user-facing implication is that Postgres data is retained even after
shutting down and/or removing the environment's containers. Minitrino issues a
warning about this whenever a module with named volumes is deployed––be sure to
look out for these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module=catalog-postgres
```
  
Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_postgres-data
```
