# File Access Control Module

A module which utilizes Trino's [file-based system access control
plugin](https://docs.starburst.io/latest/security/file-system-access-control.html).
This module also makes used of the [file-based group
provider](https://docs.starburst.io/latest/security/group-file.html).

## Usage

```sh
minitrino -v provision -m file-access-control
# Or specify Starburst version
minitrino -v -e STARBURST_VER=${version} provision -m file-access-control

docker exec -it trino bash 
trino-cli --user admin

trino> SHOW SCHEMAS FROM tpch;
```

You will need to supply a username to the Trino CLI in order to map to a group
(see `lib/modules/security/file-access-control/resources/trino/group.txt` for
which users belong to which groups). Example:

```sh
trino-cli --user admin
trino-cli --user metadata-user
trino-cli --user platform-user
```

## Policies

The access policy is located in the `rules.json` file which defines groups of
users that map to certain access control permissions. The users for the groups
are defined in the `groups.txt` file.

- Users in the `sepadmins` group have full access to all objects within Trino
- Users in the `metadata-users` group have access to the tables within the
  `system.metadata`, `system.jdbc`, and `system.information_schema` schemas
- Users in the `platform-users` group only have access to the tables within the
  `system.runtime` schema

You can modify this module to further specify access control permissions to
other catalogs provisioned with other Minitrino modules.
