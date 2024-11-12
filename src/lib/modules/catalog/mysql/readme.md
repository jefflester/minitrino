# MySQL Connector Module

This module provisions a standalone MySQL service. By default, it is exposed
both to the internal Docker network and the host via:

```yaml
ports:
  - 3306:3306
```

This will allow you to connect to the service from any SQL client that supports
MySQL drivers on `localhost:3306`.

## Usage

```sh
minitrino provision -m mysql
docker exec -it trino bash 
trino-cli
trino> show schemas from mysql;
```
