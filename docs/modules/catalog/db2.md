# Db2 Catalog

Add a [Db2 catalog](https://trino.io/docs/current/connector/db2.html) to the
cluster along with Db2 backend.

:::{admonition} Startup Might be **_Slow_** :class: important

Last I checked, Db2 doesn't work well on ARM processors, so expect the Db2
container to take a long time to start if you're running an ARM chip. :::

## Usage

{{ starburst_license_warning }}

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m db2
```

{{ connect_trino_cli }}

Confirm Db2 is reachable:

```sql
SHOW SCHEMAS FROM db2;
```
