# Starburst Gateway

Configures [Starburst
Gateway](https://docs.starburst.io/latest/admin/starburst-gateway/index.html) to
load balance access to multiple SEP clusters.

## Usage

{{ starburst_license_warning }}

:::{admonition} Harbor Registry Auth Required
:class: warning

This module requires authentication to Starburst's image registry. You must
authenticate to the Harbor registry specified in the module's YAML file before
provisioning the module:

```yaml
starburst-gateway:
  image: harbor.starburstdata.net/starburstdata/starburst-gateway:${STARBURST_GATEWAY_VER}
```

:::

Provision the module:

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m starburst-gateway
```

The module automatically provisions three Starburst clusters along with the
Gateway service itself.

### Connect to the Gateway

There are two ways to connect to the gateway:

1. Use the host endpoint (by default `localhost:9080`)
1. Use the container endpoint (by default `starburst-gateway:9080`)

To connect to the host endpoint, run the Trino CLI:

```sh
trino-cli --server localhost:9080 --user admin
```

To connect to the container endpoint, exec into the `minitrino` container and
run the Trino CLI, pointing it at the gateway container:

```sh
minitrino exec -i 'trino-cli --server starburst-gateway:9080 --user admin'
```

## Dependent Modules

- [`insights`](./insights.md#insights): Enables the Starburst web UI.
- [`faker`](../catalog/faker.md#faker): Adds a Faker catalog to each cluster for
  synthetic data.
