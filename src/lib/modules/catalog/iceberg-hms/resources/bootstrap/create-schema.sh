#!/usr/bin/env bash

before_start() {
    :
}

after_start() {
    query="CREATE SCHEMA IF NOT EXISTS iceberg_hms.minitrino \
        WITH (location='s3a://minitrino/minitrino_iceberg_hms/minitrino/');"
    trino-cli \
        --execute "${query}" --user admin
}
