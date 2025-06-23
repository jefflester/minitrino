# MinIO Module

This module deploys MinIO for a local object storage solution. It is used by
other modules to store data files, such as the `hive`, `iceberg`, and
`delta-lake` modules.

The MinIO UI can be viewed at `http://localhost:${__PORT_MINIO}` using
`access-key` and `secret-key` for credentials.

## Persistent Storage

This module uses named volumes to persist MinIO and metastore data:

```yaml
volumes:
  minio-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.admin.minio=true
```

The user-facing implication is that the data in the MinIO buckets are retained
even after shutting down and/or removing the environment's containers.

Minitrino issues a warning about this whenever a module with named volumes is
deployed––be sure to look out for these warnings:

```text
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.admin.minio=true
```
