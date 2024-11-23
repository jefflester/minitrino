# Elasticsearch Catalog Module

This module contains an ES container with some preloaded data. It contains: a
schema (ES mapping), a table (ES doc mapping), and 500 rows of fake data (ES
docs).

## Usage

```sh
minitrino -v provision -m elasticsearch
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m elasticsearch

docker exec -it trino bash 
trino-cli

trino> SHOW SCHEMAS FROM elasticsearch;
```

## Loading Data

Elasticsearch is exposed on `localhost:9200`, so additional data can be loaded
as follows:

```sh
# Create user index
curl -XPUT http://localhost:9200/user?pretty=true;
# Create user mapping
curl -XPUT http://localhost:9200/user/_mapping/profile?include_type_name=true -H 'Content-Type: application/json'-d '
{
  "profile": {
    "properties": {
      "full_name": {
        "type": "text",
        "store": true
      },
      "bio": {
        "type": "text",
        "store": true
      },
      "age": {
        "type": "integer"
      },
      "location": {
        "type": "geo_point"
      },
      "enjoys_coffee": {
        "type": "boolean"
      },
      "created_on": {
        "type": "date",
        "format": "date_time"
      }
    }
  }
}
';
# Create user profile records
curl -XPOST http://localhost:9200/user/profile/1?pretty=true -H 'Content-Type: application/json' -d '
{
  "full_name": "Andrew Puch",
  "bio": "My name is Andrew. I have a short bio.",
  "age": 26,
  "location": "41.1246110,-73.4232880",
  "enjoys_coffee": true,
  "created_on": "2015-05-02T14:45:10.000-04:00"
}
';
```

If scripting fake data is preferable, reference the bootstrap script leveraged
by this module, located at:

```sh
lib/modules/catalog/elasticsearch/resources/bootstrap/bootstrap-elasticsearch.sh
```

## Persistent Storage

This module uses named volumes to persist ES data:

```yaml
volumes:
  elasticsearch-data:
    labels:
      - com.starburst.tests=minitrino
      - com.starburst.tests.module.elasticsearch=catalog-elasticsearch
```

The user-facing implication is that ES data is retained even after shutting down
and/or removing the environment's containers. Minitrino issues a warning about
this whenever a module with named volumes is deployed––be sure to look out for
these warnings:

```log
[w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.
```

To remove these volumes, run:

```sh
minitrino -v remove --volumes --label com.starburst.tests.module.elasticsearch=catalog-elasticsearch
```
  
Or, remove them directly using the Docker CLI:

```sh
docker volume rm minitrino_elasticsearch-data
```
