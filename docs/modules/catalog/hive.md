# Hive Catalog Module

This module deploys the necessary components for a Hive environment.

- **Metastore**: served via a Hive metastore (`metastore-hive` container backed
  by `postgres-hive` for storage)
  - The HMS image is based off of naushadh's repository
    [here](https://github.com/naushadh/hive-metastore) (refer to his repository
    for additional documentation on the HMS image and configuration options)

Tables backed by ORC data files can be easily created:

```sql
CREATE SCHEMA hive.tiny WITH (location='s3a://minitrino/wh/tiny/');
CREATE TABLE hive.tiny.customer AS SELECT * FROM tpch.tiny.customer;
```

## Usage

```sh
minitrino -v provision -m hive
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m hive

docker exec -it minitrino bash 
trino-cli

trino> SHOW SCHEMAS FROM hive;
```

## Persistent Storage

This module uses named volumes to persist metastore data:

```yaml
volumes:
  postgres-hive-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.hive=true
```

The user-facing implication is that the data in the Hive metastore is retained
even after shutting down and/or removing the environment's containers. Minitrino
issues a warning about this whenever a module with named volumes is deployed––be
sure to look out for these warnings:

```text
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.catalog.hive=true
```
