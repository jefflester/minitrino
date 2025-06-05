# Results Cache Module

This module deploys the necessary components for Starburst Enterprise result
caching.

- **Object storage**: served via MinIO (`minio-results-cache` container and
  bootstrapped by `create-minio-results-cache-buckets`)

The MinIO UI can be viewed at `http://localhost:9004` using `access-key` and
`secret-key` for credentials. Result cache data will be stored in
`s3a://sample-bucket/sep-results-cache/`.

## Usage

```sh
minitrino -v provision -m results-cache
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m results-cache

docker exec -it minitrino bash 
trino-cli

# Run query multiple times in a row - subsequent executions should be cached
trino> SELECT * FROM <TABLE> LIMIT 10;
```

## Persistent Storage

This module uses named volumes to persist MinIO data:

```yaml
volumes:
  minio-results-cache-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.admin.results-cache=true
```

The user-facing implication is that the data files stored in MinIO are retained
even after shutting down and/or removing the environment's containers. Minitrino
issues a warning about this whenever a module with named volumes is deployed––be
sure to look out for these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.admin.results-cache=true
```

Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_minio-results-cache-data
```
