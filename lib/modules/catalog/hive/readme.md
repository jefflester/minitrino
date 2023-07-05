# Hive Module

This module uses Minio as a local S3 service. You can write data to this service
and the files will be written to your machine. You can read more about Minio
[here](https://docs.min.io/docs/minio-docker-quickstart-guide.html). This module
also uses a Hive metastore (HMS) container along with a Postgres container for
the HMS's backend storage. The HMS image is based off of naushadh's repository
[here](https://github.com/naushadh/hive-metastore) (refer to his repository for
additional documentation on the HMS image and configuration options).

You can access the Minio UI at `http://localhost:9001` with `access-key` and
`secret-key` for credentials.

You can create a table with ORC data with Trino very quickly:

    trino> create schema hive.tiny with (location='s3a://sample-bucket/wh/tiny/');
    CREATE SCHEMA

    trino> create table hive.tiny.customer as select * from tpch.tiny.customer;
    CREATE TABLE: 1500 rows

You will see the ORC data stored in your local Minio bucket.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module hive
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from hive;
