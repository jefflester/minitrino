# MySQL Catalog Module

This module provisions a standalone MySQL service. By default, it is exposed
both to the internal Docker network and the host via:

```yaml
ports:
  - 3306:3306
```

This will allows users to connect to the service from any SQL client that
supports MySQL drivers on `localhost:3306`.

## Usage

```sh
minitrino -v provision -m mysql
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m mysql

docker exec -it trino bash 
trino-cli
trino> SHOW SCHEMAS FROM mysql;
```
