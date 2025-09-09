# Faker Catalog

Add a [Faker catalog](https://trino.io/docs/current/connector/faker.html) to the
cluster.

## Usage

Provision the module:

```sh
minitrino provision -m faker
```

{{ connect_trino_cli }}

Create a table:

```sql
CREATE TABLE faker.default.test (a VARCHAR);
SELECT * FROM faker.default.test;
```

`faker.default.test` should return fake data when queried.
