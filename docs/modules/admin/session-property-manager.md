# Session Property Manager

Configures the file-based
[session property manager](https://trino.io/docs/current/admin/session-property-managers.html)
in the cluster.

## Usage

Provision the module:

```sh
minitrino provision -m session-property-manager
```

{{ connect_trino_cli_admin }}

```sql
SELECT 1;
```

The resource groups will apply to all users, with varying weights and priorities
assigned to certain user groups. Session properties applied to queries can be
viewed on the query details through the Trino web UI at `localhost:8080/ui/`.

The session property JSON file is mounted to the cluster as a volume and can be
viewed/edited within the container:

```sh
minitrino exec -i \
    'vi /etc/${CLUSTER_DIST}/session-property.json'
```

## Dependent Modules

- [`file-group-provider`](./file-group-provider.md): Used to define user groups.
- [`resource-groups`](./resource-groups.md): Used to define resource groups.
