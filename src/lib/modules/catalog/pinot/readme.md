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

## Persistent Storage

This module uses named volumes to persist Zookeeper, Pinot controller, and Pinot
server data:

```yaml
volumes:
  pinot-zookeeper-data:
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.pinot=catalog-pinot
  pinot-zookeeper-datalog:
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.pinot=catalog-pinot
  pinot-controller-data:
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.pinot=catalog-pinot
  pinot-server-data:
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.pinot=catalog-pinot
```

The user-facing implication is that the data stored in Zookeeper as well as the
Pinot components are retained even after shutting down and/or removing the
environment's containers. Minitrino issues a warning about this whenever a
module with named volumes is deployed––be sure to look out for these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label com.starburst.tests.module.pinot=catalog-pinot
```
  
Or, remove them directly using the Docker CLI:

```sh
docker volume rm \
  pinot-zookeeper-data \
  pinot-zookeeper-datalog \
  minitrino_pinot-controller-data \
  minitrino_pinot-server-data
```
