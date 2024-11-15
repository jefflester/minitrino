# Iceberg Catalog Module

This module deploys infrastructure for an Iceberg catalog leveraging the Iceberg
REST catalog.

MinIO is used for a local S3 server and leverages [virtual-hosted style
requests](https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html#virtual-hosted-style-access).

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module iceberg
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from hive;

Create a schema and a table:

    create schema iceberg.test with (location = 's3a://sample-bucket/wh/test');
    create table iceberg.test.test_tbl as select * from tpch.tiny.customer;

## Persistent Storage

This module uses named volumes to persist MinIO data:

    volumes:
      minio-iceberg-data:
        labels:
          - com.starburst.tests=minitrino
          - com.starburst.tests.module.iceberg=catalog-iceberg

The user-facing implication is that the data files stored in MinIO are retained
even after shutting down and/or removing the environment's containers. Minitrino
issues a warning about this whenever a module with named volumes is deployed––be
sure to look out for these warnings:

    [w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.

To remove these volumes, run:

    minitrino -v remove --volumes --label com.starburst.tests.module.iceberg=catalog-iceberg
  
Or, remove them directly using the Docker CLI:

    docker volume rm minitrino_minio-iceberg-data

## Editing the `iceberg.properties` File

This module uses a roundabout way to mount the `iceberg.properties` file that
allows for edits to be made to the file inside the Trino container without the
source file being modified on the host. To edit the file, exec into the Trino
container, make the desired changes, and then restart the container for the
changes to take effect:

    docker exec -it trino bash 
    vi /etc/starburst/catalog/iceberg.properties
    exit

    docker restart trino

The properties file can also be edited directly from the module directory prior
to provisioning the module:

    lib/modules/catalog/<module>/resources/trino/<module>.properties
