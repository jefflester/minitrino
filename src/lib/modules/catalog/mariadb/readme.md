# MariaDB Connector Module

This module provisions a standalone MariaDB service. By default, it is exposed
to the internal Docker network only via:

```yaml
ports:
  - :3306
```

To expose it at the host level, add a port to the left of the colon, e.g.:

```yaml
ports:
  - 3307:3306
```

This will allow you to connect to the service from any SQL client that supports
MariaDB drivers on `localhost:3307`.

## Usage

```sh
minitrino provision -m mariadb
docker exec -it trino bash 
trino-cli
trino> show schemas from mariadb;
```
