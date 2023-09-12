#!/usr/bin/env bash

set -euxo pipefail

curl -fsSL https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh \
    > /tmp/wait-for-it.sh \

chmod +x /tmp/wait-for-it.sh

echo "Waiting for MinIO to come up..."
/tmp/wait-for-it.sh minio-iceberg:9000 --strict --timeout=60 -- echo "MinIO service is up."

/usr/bin/mc alias set minio http://minio-iceberg:9000 access-key secret-key
/usr/bin/mc mb minio/sample-bucket/wh/
