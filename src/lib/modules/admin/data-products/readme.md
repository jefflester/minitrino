# Data Products Module  

A module which configures Starburst's [data
products](https://docs.starburst.io/latest/data-products.html) feature.

The `hive` and `insights` modules are dependencies of this module.

## Usage

```sh
minitrino -v provision -m data-products
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m data-products

docker exec -it minitrino bash 
trino-cli

trino> SHOW SCHEMAS FROM backend_svc;
```

When configuring data product domains, use this `s3a` path, which is from a
bucket auto-provisioned in the related MinIO container:

```txt
s3a://minitrino/<domain>
```
