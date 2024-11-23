#!/bin/bash

set -e

echo "Creating three sample tables..."

clickhouse client -n <<-EOSQL
    CREATE TABLE IF NOT EXISTS minitrino.table1 (
        id UInt32,
        name String,
        value Float64
    ) ENGINE = MergeTree()
    ORDER BY id;

    CREATE TABLE IF NOT EXISTS minitrino.table2 (
        id UInt32,
        category String,
        amount Decimal(10, 2)
    ) ENGINE = MergeTree()
    ORDER BY id;

    CREATE TABLE IF NOT EXISTS minitrino.table3 (
        id UInt32,
        timestamp DateTime,
        is_active UInt8
    ) ENGINE = MergeTree()
    ORDER BY id;

    -- Insert random data into table1 only if there are fewer than 1000 rows
    INSERT INTO minitrino.table1
    SELECT
        number AS id,
        concat('Name_', toString(number % 100)) AS name,
        rand() % 10000 / 100.0 AS value
    FROM numbers(1000)
    WHERE (SELECT count() FROM minitrino.table1) < 1000;

    -- Insert random data into table2 only if there are fewer than 1000 rows
    INSERT INTO minitrino.table2
    SELECT
        number AS id,
        concat('Category_', toString(rand() % 10)) AS category,
        rand() % 5000 / 100.0 AS amount
    FROM numbers(1000)
    WHERE (SELECT count() FROM minitrino.table2) < 1000;

    -- Insert random data into table3 only if there are fewer than 1000 rows
    INSERT INTO minitrino.table3
    SELECT
        number AS id,
        now() - number * 60 AS timestamp,
        rand() % 2 AS is_active
    FROM numbers(1000)
    WHERE (SELECT count() FROM minitrino.table3) < 1000;
EOSQL
