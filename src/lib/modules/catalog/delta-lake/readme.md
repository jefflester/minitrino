# Delta-Lake Module

This module uses Minio as a local S3 service. You can write data to this service
and the files will be written to your machine. You can read more about Minio
[here](https://docs.min.io/docs/minio-docker-quickstart-guide.html). This module
also uses a Hive metastore (HMS) container along with a Postgres container for
the HMS's backend storage. The HMS image is based off of naushadh's repository
[here](https://github.com/naushadh/hive-metastore) (refer to his repository for
additional documentation on the HMS image and configuration options).

You can access the Minio UI at `http://localhost:9002` with `access-key` and
`secret-key` for credentials.

This module uses the Delta Lake connector. There is no Spark backend, so tables
need to be created via `CREATE TABLE AS ...` queries from Trino. Example:

    CREATE TABLE delta.default.customer 
    WITH (
        location = 's3a://sample-bucket/wh/default/'
    )
    AS SELECT * FROM tpch.tiny.customer;

This will create the table `delta.default.customer` and a corresponding
`_delta_log` directory in the backing MinIO object storage.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module delta-lake
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from delta;

## Cleanup

This module uses named volumes to persist MinIO and HMS data:

    volumes:
      postgres-delta-lake-data:
        labels:
          - com.starburst.tests=minitrino
          - com.starburst.tests.module.delta-lake=catalog-delta-lake
      minio-delta-lake-data:
        labels:
          - com.starburst.tests=minitrino
          - com.starburst.tests.module.delta-lake=catalog-delta-lake

To remove these volumes, run:

    minitrino -v remove --volumes --label com.starburst.tests.module.delta-lake=catalog-delta-lake
