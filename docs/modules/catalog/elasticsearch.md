# Elasticsearch Catalog

Add an [Elasticsearch
catalog](https://trino.io/docs/current/connector/elasticsearch.html) to the
cluster along with an ES container with some preloaded data.

## Usage

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino provision -m elasticsearch
```

{{ connect_trino_cli }}

Confirm Elasticsearch is reachable:

```sql
SHOW SCHEMAS FROM elasticsearch;
```

## Loading Data

The Elasticsearch REST API is exposed on `localhost:9200`. Data can be loaded
through that, or by using the script provided in the module:

```sh
lib/modules/catalog/elasticsearch/resources/cluster/bootstrap-es.sh
```
