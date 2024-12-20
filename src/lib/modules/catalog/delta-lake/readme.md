# Delta Lake Catalog Module

This module deploys the necessary components for a Delta Lake environment.

- **Object storage**: served via MinIO (`minio-delta-lake` container and
  bootstrapped by `create-minio-delta-lake-buckets`)
- **Metastore**: served via a Hive metastore (`metastore-delta-lake` container
  backed by `postgres-delta-lake` for storage)
  - The HMS image is based off of naushadh's repository
    [here](https://github.com/naushadh/hive-metastore) (refer to his repository
    for additional documentation on the HMS image and configuration options)

The MinIO UI can be viewed at `http://localhost:9002` using `access-key` and
`secret-key` for credentials.

This module uses the Delta Lake connector. There is no Spark backend, so tables
need to be created via `CREATE TABLE AS ...` queries from Trino. Example:

```sql
CREATE TABLE delta.default.customer 
WITH (
    location = 's3a://sample-bucket/wh/default/'
)
AS SELECT * FROM tpch.tiny.customer;
```

This will create the table `delta.default.customer` and a corresponding
`_delta_log` directory in MinIO object storage.

## Usage

```sh
minitrino -v provision -m delta-lake
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m delta-lake

docker exec -it trino bash 
trino-cli

trino> SHOW SCHEMAS FROM delta;
```

## Persistent Storage

This module uses named volumes to persist MinIO and metastore data:

```yaml
volumes:
  postgres-delta-lake-data:
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.delta-lake=catalog-delta-lake
  minio-delta-lake-data:
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.delta-lake=catalog-delta-lake
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
minitrino -v remove --volumes --label com.starburst.tests.module.delta-lake=catalog-delta-lake
```
  
Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_postgres-delta-lake-data \
  minitrino_minio-delta-lake-data
```

## Editing the `delta.properties` File

This module uses a roundabout way to mount the `delta.properties` file that
allows for edits to be made to the file inside the Trino container without the
source file being modified on the host. To edit the file, exec into the Trino
container, make the desired changes, and then restart the container for the
changes to take effect:

```sh
docker exec -it trino bash 
vi /etc/starburst/catalog/delta.properties
exit

docker restart trino
```

The properties file can also be edited directly from the module directory prior
to provisioning the module:

```txt
lib/modules/catalog/<module>/resources/trino/<module>.properties
```
