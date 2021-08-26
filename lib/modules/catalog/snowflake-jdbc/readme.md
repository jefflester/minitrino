# Snowflake JDBC Connector Module

This module hooks up to an externally-hosted Snowflake service and leverages the
[JDBC Snowflake
connector](https://docs.starburst.io/latest/connector/starburst-snowflake.html).

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module snowflake-jdbc
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from snowflake_jdbc;
