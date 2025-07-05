# Resource Groups

Configures [resource
groups](https://trino.io/docs/current/admin/resource-groups.html) in the
cluster.

## Usage

Provision the module:

```sh
minitrino provision -m resource-groups
```

{{ connect_trino_cli_admin }}

```sql
SELECT 1;
```

The resource groups will apply to all users with varying weights and priorities
assigned to certain user groups. Resource groups active during query execution
can be viewed on the query details through the Trino web UI at
`localhost:8080/ui/`. They can also be viewed through SQL via
`system.runtime.queries`, e.g.:

```sql
SELECT resource_group_id FROM system.runtime.queries 
WHERE query = 'SELECT 1' AND user = 'admin';
```

The resource group definitions are mounted to the cluster as a volume and can be
viewed/edited within the container:

```sh
minitrino exec -i \
    'vi /etc/${CLUSTER_DIST}/resource-groups.json'

minitrino restart
```

## Dependent Modules

- [`file-group-provider`](./file-group-provider.md#file-group-provider):
  Required for group definitions.
