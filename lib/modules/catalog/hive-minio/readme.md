# Hive-Minio Module
This module uses Minio as a local implementation of S3 object storage. You can write data to this service, and the files will be written to your machine. You can read more about Minio [here](https://docs.min.io/docs/minio-docker-quickstart-guide.html). This module also uses a Hive metastore container along with a Postgres container for the metastore's backend storage.

You can access the Minio UI at `http://localhost:9000` with `access-key` and `secret-key` for credentials. 

You can create a table with ORC data with Trino very quickly:

```
trino> create schema hive_hms_minio.tiny with (location='s3a://sample-bucket/tiny/');
CREATE SCHEMA

trino> create table hive_hms_minio.tiny.customer as select * from tpch.tiny.customer;
CREATE TABLE: 1500 rows
```

You will see the ORC data stored in your local Minio bucket.

Note the [relevant commit](https://github.com/starburstdata/docker-images/commit/6b29c2359a173ca6971267fa05191258b1964c8b#diff-8961ce993089ebecf98d0457b676e626) for the property `S3_PATH_STYLE_ACCESS` in `hms.env`.
