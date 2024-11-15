# Data Products Module  

A module which configures the [data
products](https://docs.starburst.io/latest/data-products.html) feature.

The `hive` and `insights` modules are dependencies of this module.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module data-products
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from backend_svc;

For configuring data product domains, use this `s3a` path, which is from a
bucket auto-provisioned in the related MinIO container:

    s3a://sample-bucket/<domain>
