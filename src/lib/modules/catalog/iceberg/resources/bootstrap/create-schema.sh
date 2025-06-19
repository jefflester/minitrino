#!/usr/bin/env bash

before_start() {
    :
}

after_start() {
    query="CREATE SCHEMA IF NOT EXISTS iceberg.minitrino_iceberg \
        WITH (location='s3a://minitrino/minitrino_iceberg');"
    trino-cli \
        --execute "${query}" --user admin
}
