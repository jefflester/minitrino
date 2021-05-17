# File Access Control Module
A module which utilizes Trino's [file-based system access control
plugin](https://docs.starburst.io/latest/security/file-system-access-control.html).
This also makes used of the [file-based group
provider](https://docs.starburst.io/latest/security/group-file.html).

## Sample Usage
To provision this module, run:

```shell
minitrino provision --module file-access-control
```

You will need to supply a username to the Trino CLI in order to map to a group
(see `group.txt` for which users belong to which groups). Example:

```shell
trino-cli --user admin-2
trino-cli --user metadata-1
trino-cli --user platform
```

## Policies
The access policy is located in the `rules.json` file which defines groups of
users that map to a certain access control permission. The users for the groups
are defined in the `group.txt` file.

- Users in the `platform-admins` group have full access to all objects within Trino
- Users in the `metadata-users` group only have access to the tables within the
  `system.metadata` schema
- Users in the `platform-users` group only have access to the tables within the
  `system.runtime` schema

You can modify this module to further specify access control permissions to
other catalogs provisioned with other Minitrino modules.
