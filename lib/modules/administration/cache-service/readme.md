# Cache Service Module

This module sets up the [Starburst cache
service](https://docs.starburst.io/latest/admin/cache-service.html), which is
leveraged by materialized views and table scan redirections.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module cache-service
