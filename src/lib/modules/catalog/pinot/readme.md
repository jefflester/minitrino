# Pinot Catalog Module

This module adds a Pinot catalog to Trino and provisions a Pinot cluster with
all the main Pinot components:

- Zookeeper for metadata management
- Pinot controller
- Pinot broker
- Pinot server

A bootstrap script loads various sample data sets included with the Pinot Docker
image.

## Usage

To deploy the module:

```sh
minitrino -v provision -m pinot
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m pinot

docker exec -it trino bash 
trino-cli

trino> SHOW SCHEMAS FROM pinot;
```

The Pinot web UI can be viewed at `localhost:9090`.
