# Hive Catalog Module

This module deploys the necessary components for a Delta Lake environment.

- **Object storage**: served via MinIO (`minio` container and bootstrapped by
  `create-minio-buckets`)
- **Metastore**: served via a Hive metastore (`metastore-hive` container backed
  by `postgres-hive` for storage)
  - The HMS image is based off of naushadh's repository
    [here](https://github.com/naushadh/hive-metastore) (refer to his repository
    for additional documentation on the HMS image and configuration options)

The MinIO UI can be viewed at `http://localhost:9001` using `access-key` and
`secret-key` for credentials.

Tables backed by ORC data files can be easily created:

    trino> create schema hive.tiny with (location='s3a://sample-bucket/wh/tiny/');
    CREATE SCHEMA

    trino> create table hive.tiny.customer as select * from tpch.tiny.customer;
    CREATE TABLE: 1500 rows

The ORC data files can be viewed directly in the MinIO bucket via the MinIO UI.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module hive
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from hive;

## Persistent Storage

This module uses named volumes to persist MinIO and metastore data:

    volumes:
      postgres-hive-data:
        labels:
          - com.starburst.tests=minitrino
          - com.starburst.tests.module.hive=catalog-hive
      minio-hive-data:
        labels:
          - com.starburst.tests=minitrino
          - com.starburst.tests.module.hive=catalog-hive

The user-facing implication is that the data in the Hive metastore and the data
files stored in MinIO are retained even after shutting down and/or removing the
environment's containers. Minitrino issues a warning about this whenever a
module with named volumes is deployed––be sure to look out for these warnings:

    [w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.

To remove these volumes, run:

    minitrino -v remove --volumes --label com.starburst.tests.module.hive=catalog-hive

Or, remove them directly using the Docker CLI:

    docker volume rm minitrino_postgres-hive-data minitrino_minio-hive-data

## Editing the `hive.properties` File

This module uses a roundabout way to mount the `hive.properties` file that
allows for edits to be made to the file inside the Trino container without the
source file being modified on the host. To edit the file, exec into the Trino
container, make the desired changes, and then restart the container for the
changes to take effect:

    docker exec -it trino bash 
    vi /etc/starburst/catalog/hive.properties
    exit

    docker restart trino
