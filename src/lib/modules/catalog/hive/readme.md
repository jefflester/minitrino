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

```sql
CREATE SCHEMA hive.tiny WITH (location='s3a://sample-bucket/wh/tiny/');
CREATE TABLE hive.tiny.customer AS SELECT * FROM tpch.tiny.customer;
```

The ORC data files can be viewed directly in the MinIO bucket via the MinIO UI.

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

This module uses named volumes to persist MinIO and metastore data:

```yaml
volumes:
  postgres-hive-data:
    labels:
      - org.minitrino=root
      - org.minitrino.module.hive=catalog-hive
  minio-hive-data:
    labels:
      - org.minitrino=root
      - org.minitrino.module.hive=catalog-hive
```

The user-facing implication is that the data in the Hive metastore and the data
files stored in MinIO are retained even after shutting down and/or removing the
environment's containers. Minitrino issues a warning about this whenever a
module with named volumes is deployed––be sure to look out for these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.hive=catalog-hive
```

Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_postgres-hive-data minitrino_minio-hive-data
```

## Editing the `hive.properties` File

This module uses a roundabout way to mount the `hive.properties` file that
allows for edits to be made to the file inside cluster containers without the
source file being modified on the host. To edit the file, exec into the `minitrino`
container, make the desired changes, and then restart the container for the
changes to take effect:

```sh
docker exec -it minitrino bash 
vi /etc/"${CLUSTER_DIST}"/catalog/hive.properties
exit

docker restart minitrino
```

The properties file can also be edited directly from the module directory prior
to provisioning the module:

```txt
lib/modules/catalog/<module>/resources/cluster/<module>.properties
```
