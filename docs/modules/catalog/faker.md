# Faker Catalog Module

This module provisions the system with a [Faker
catalog](https://docs.starburst.io/latest/connector/faker.html).

## Usage

```sh
minitrino -v provision -m faker
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m faker

docker exec -it minitrino bash 
trino-cli

trino> CREATE TABLE faker.default.test (a VARCHAR);
trino> SELECT * FROM faker.default.test;
```
