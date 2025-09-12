# Pinot Catalog

Add a [Pinot catalog](https://trino.io/docs/current/connector/pinot.html) to the
cluster along with a standalone Pinot cluster.

The Pinot cluster includes all the main Pinot components:

- Zookeeper for metadata management
- Pinot controller
- Pinot broker
- Pinot server

A bootstrap script loads various sample data sets included with the Pinot Docker
image.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m pinot
```

{{ connect_trino_cli }}

Confirm Pinot is reachable:

```sql
SHOW SCHEMAS FROM pinot;
```

The Pinot web UI can be viewed at `localhost:9090`.
