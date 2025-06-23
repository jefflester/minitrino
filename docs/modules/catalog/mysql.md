# MySQL Catalog Module

This module provisions a standalone MySQL service. By default, it is exposed
both to the internal Docker network and the host via:

```yaml
ports:
  - 3306:3306
```

This will allows users to connect to the service from any SQL client that
supports MySQL drivers on `localhost:3306`.

## Usage

```sh
minitrino -v provision -m mysql
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m mysql

docker exec -it minitrino bash 
trino-cli
trino> SHOW SCHEMAS FROM mysql;
```

## Persistent Storage

This module uses named volumes to persist MySQL data:

```yaml
volumes:
  mysql-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.mysql=true
```

The user-facing implication is that MySQL data is retained even after shutting
down and/or removing the environment's containers. Minitrino issues a warning
about this whenever a module with named volumes is deployed––be sure to look out
for these warnings:

```text
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.catalog.mysql=true
```

Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_mysql-data
```
