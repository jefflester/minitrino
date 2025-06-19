#!/usr/bin/env bash

before_start() {
    :
}

after_start() {
    query="CREATE SCHEMA IF NOT EXISTS delta.minitrino_delta_lake \
        WITH (location='s3a://minitrino/minitrino_delta_lake');"
    trino-cli \
        --execute "${query}" --user admin
}
