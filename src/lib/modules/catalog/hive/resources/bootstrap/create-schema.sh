#!/usr/bin/env bash

before_start() {
    :
}

after_start() {
    query="CREATE SCHEMA IF NOT EXISTS hive.minitrino_hive \
        WITH (location='s3a://minitrino/minitrino_hive');"
    trino-cli \
        --execute "${query}" --user admin
}
