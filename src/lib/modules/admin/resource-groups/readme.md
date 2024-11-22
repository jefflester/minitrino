# Resource Groups Module

A module which implements Trino's [resource group
functionality](https://docs.starburst.io/latest/admin/resource-groups.html).

Leverages the `file-group-provider` module to define various user groups within
the system.

## Usage

```sh
minitrino -v provision -m resource-groups
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m resource-groups

# Get into the container and connect as a user tied to a group
docker exec -it trino bash 
trino-cli --user admin

trino> SELECT 1;
```

The resource groups will apply to all users, with varying weights and priorities
assigned to certain user groups. Resource groups active at/during query
execution can be viewed on the query details through the Trino web UI at
`localhost:8080/ui/`. They can also be viewed through SQL via
`system.runtime.queries`, e.g.:

```sql
SELECT resource_group_id FROM system.runtime.queries WHERE query = 'select 1' AND user = 'admin';
```

The resource group definitions are mounted to Trino as a volume and can be
viewed/edited within the container:

```sh
docker exec -it trino bash 
vi /etc/starburst/resource-groups.json
```

Alternatively, it can be edited directly in the library:

```sh
lib/modules/admin/resource-groups/resources/trino/resource-groups.json
```
