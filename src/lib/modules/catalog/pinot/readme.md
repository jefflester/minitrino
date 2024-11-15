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

    minitrino --env STARBURST_VER=<ver> provision --module pinot
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from pinot;

The Pinot web UI can be viewed at `localhost:9090`.
