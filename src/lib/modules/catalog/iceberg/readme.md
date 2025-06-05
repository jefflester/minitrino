# Iceberg Catalog Module

This module deploys infrastructure for an Iceberg catalog leveraging the Iceberg
REST catalog.

MinIO is used for a local S3 server and leverages [virtual-hosted style
requests](https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html#virtual-hosted-style-access).

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
CREATE SCHEMA iceberg.test WITH (location = 's3a://sample-bucket/wh/test');
CREATE TABLE iceberg.test.test_tbl AS SELECT * FROM tpch.tiny.customer;
```

## Persistent Storage

This module uses named volumes to persist Iceberg metadata and MinIO data:

```yaml
volumes:
  iceberg-metadata:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.iceberg=true
  minio-iceberg-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.iceberg=true
```

The user-facing implication is that the Iceberg's metadata and the data files
stored in MinIO are retained even after shutting down and/or removing the
environment's containers. Minitrino issues a warning about this whenever a
module with named volumes is deployed––be sure to look out for these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.catalog.iceberg=true
```
  
Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_iceberg-metadata minitrino_minio-iceberg-data
```
