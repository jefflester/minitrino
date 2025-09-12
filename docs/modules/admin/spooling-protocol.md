# Spooling Protocol

Adds the
[spooling protocol](https://docs.starburst.io/latest/client/client-protocol.html#protocol-spooling)
to the cluster.

## Usage

Provision the module:

```sh
minitrino provision -m spooling-protocol
```

## Dependent Modules

- [`minio`](./minio.md): Used for storing spooled data.
