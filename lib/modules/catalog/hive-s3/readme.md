# Hive-S3 Module

This module uses a Hive metastore container along with a Postgres container for
the metastore's backend storage. Using Minitrino's config file, you can input
AWS credentials to link the module to a an S3 bucket for data storage, reading,
and writing. Removing the volume associated with the Postgres container will
effectively remove your metastore's database, so only remove the volume if you
are prepared to lose all of your metadata.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module hive-s3
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from hive_s3;
