# Iceberg Module

This module deploys infrastructure for an Iceberg catalog leveraging the Iceberg
REST catalog.

MinIO is used for a local S3 server and leverages [virtual-hosted style
requests](https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html#virtual-hosted-style-access).

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module iceberg

## Cleanup

This module uses a named volume to persist MinIO data:

    volumes:
      minio-iceberg-data:
        labels:
          - com.starburst.tests=minitrino
          - com.starburst.tests.module.iceberg=catalog-iceberg

To remove this volume, run:

    minitrino -v remove --volumes --label com.starburst.tests.module.iceberg=catalog-iceberg
