# System-Level Ranger Access Control Module

This module provisions a Ranger server and Postgres database for Ranger storage.
It is an unsecured deployment without SSL or an authentication mechanism.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module system-ranger
    docker exec -it trino bash 
    trino-cli --user bob
    trino> select * from tpch.sf100.customer limit 1;

## Requirements

- Starburst Data license
- Access to Starburst Data Harbor repository for Docker images

## Policies

- Bob: admin access to TPCH `sf100` schema
- Alice: admin access to TPCH `sf10` schema

## Accessing Ranger

- Go to `localhost:6080`
- Sign in with user: `admin` and password: `trinoRocks15`
