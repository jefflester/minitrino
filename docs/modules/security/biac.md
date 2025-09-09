# Built-in Access Control

Enable
[built-in access control (BIAC)](https://docs.starburst.io/latest/security/biac-overview.html).

## Usage

{{ starburst_license_warning }}

Provision the module:

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m biac
```

Connect to the coordinator container's Trino CLI:

```sh
minitrino exec -i 'trino-cli --user admin'
```

Confirm role membership:

```sql
SET ROLE sysadmin;
SHOW ROLES;
```

```text
   Role
----------
 public
 sysadmin
```

## Default Roles

BIAC is deployed with the following default roles:

```{table}
| Role      | Description                                                |
|:----------|:----------------------------------------------------------|
| `public`  | Public role (baseline access granted to all users)         |
| `sysadmin`| System administrator (baseline access granted to authorized users*) |
```

```{note}
*Authorized users are defined in the `starburst.access-control.authorized-users` (`admin`) and `starburst.access-control.authorized-groups` (`clusteradmins`) properties.*
```

## Dependent Modules

- [`insights`](../admin/insights.md#insights): Enables the Starburst web UI and
  configures a backend database for persisting BIAC entities.
