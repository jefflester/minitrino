# Db2 Catalog Module

This module provisions a standalone Db2 service.

**Note for Mac M-chip users**: the Db2 service can take a *long* time to start
(10-20+ minutes), so ensure you are viewing the Db2 container logs to check the
status of the service. If you receive a `connection refused` error from SEP ->
Db2, chances are that Db2 has not started yet.

## Usage

```sh
minitrino -v provision -m db2
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m db2

docker exec -it trino bash 
trino-cli

trino> SHOW SCHEMAS FROM db2;
```
