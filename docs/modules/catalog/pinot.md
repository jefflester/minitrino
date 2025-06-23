# Pinot Catalog Module

This module adds a Pinot catalog and provisions a Pinot cluster with all the
main Pinot components:

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
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m pinot

docker exec -it minitrino bash 
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
      - org.minitrino.root=true
      - org.minitrino.module.catalog.pinot=true
  pinot-zookeeper-datalog:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.pinot=true
  pinot-controller-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.pinot=true
  pinot-server-data:
    labels:
      - org.minitrino.root=true
      - org.minitrino.module.catalog.pinot=true
```

The user-facing implication is that the data stored in Zookeeper as well as the
Pinot components are retained even after shutting down and/or removing the
environment's containers. Minitrino issues a warning about this whenever a
module with named volumes is deployed––be sure to look out for these warnings:

```text
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label org.minitrino.module.catalog.pinot=true
```

Or, remove them directly using the Docker CLI:

```sh
docker volume rm \
  pinot-zookeeper-data \
  pinot-zookeeper-datalog \
  minitrino_pinot-controller-data \
  minitrino_pinot-server-data
```
