# Stargate Parallel Catalog

Add a
[Stargate parallel catalog](https://docs.starburst.io/latest/connector/starburst-stargate.html)
to the cluster along with a remote Stargate cluster for catalog access.

## Usage

{{ starburst_license_warning }}

Provision the module:

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m stargate-parallel
```

This module spins up an additional cluster to serve as the remote Stargate
cluster.

{{ connect_trino_cli }}

Confirm Stargate is reachable:

```sql
SHOW SCHEMAS FROM stargate_parallel;
```

## Dependent Modules

The remote cluster depends on the following modules:

- [`hive`](./hive.md#hive-catalog)
- [`password-file`](../security/password-file.md)
- [`spooling-protocol`](../admin/spooling-protocol.md): Required specifically for
  the parallel connector.
