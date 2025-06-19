# Results Cache Module

This module deploys Starburst Enterprise result caching.

## Usage

```sh
minitrino -v provision -m results-cache
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m results-cache

docker exec -it minitrino bash 
trino-cli

# Run query multiple times in a row - subsequent executions should be cached
trino> SELECT * FROM <TABLE> LIMIT 10;
```
