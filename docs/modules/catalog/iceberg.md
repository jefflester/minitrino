# Iceberg Catalog Module

This module deploys infrastructure for an Iceberg catalog leveraging the Iceberg
REST catalog.

## Usage

```sh
minitrino -v provision -m iceberg
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m iceberg

docker exec -it minitrino bash 
trino-cli

trino> SHOW SCHEMAS FROM iceberg;
```

Create a schema and a table:

```sql
CREATE SCHEMA iceberg.test WITH (location = 's3a://minitrino/wh/test');
CREATE TABLE iceberg.test.test_tbl AS SELECT * FROM tpch.tiny.customer;
```

## Persistent Storage

This module uses named volumes to persist Iceberg metadata:

```yaml
volumes:
  iceberg-metadata:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.iceberg=true
```

The user-facing implication is that the Iceberg's metadata is retained even
after shutting down and/or removing the environment's containers. Minitrino
issues a warning about this whenever a module with named volumes is deployed––be
sure to look out for these warnings:

```text
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.catalog.iceberg=true
```
