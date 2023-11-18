# Data Products Module  

A module which deploys the Starburst [data
products](https://docs.starburst.io/latest/data-products.html) feature.

The `hive` and `insights` modules are dependencies of this module.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module data-products
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from query_logger;
