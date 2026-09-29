# MinIO

Add a MinIO container for local object storage – used by other modules to store
data files, such as the `hive`, `iceberg`, and `delta-lake` modules.

```{note}
MinIO no longer publishes community images to Docker Hub. This module uses the
community-maintained [`pgsty/minio`](https://hub.docker.com/r/pgsty/minio) and
[`pgsty/mc`](https://hub.docker.com/r/pgsty/mc) forks, pinned via the
`MINIO_VER` and `MINIO_MC_VER` environment variables.
```

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m minio
```

The MinIO UI can be viewed at `http://localhost:9000` using `access-key` and
`secret-key` for credentials.

The default bucket is `minitrino`. The MinIO client can be accessed by utilizing
the `minio-client` container:

```sh
minitrino exec -c minio-client -i
mc ls minio/minitrino/
```

```text
[2025-07-05 08:33:37 UTC]     0B minitrino_hive/
[2025-07-05 08:33:37 UTC]     0B minitrino_iceberg/
```
