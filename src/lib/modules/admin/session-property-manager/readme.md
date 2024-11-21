# Session Property Manager Module

A module which implements Trino's file-based [session property
manager](https://docs.starburst.io/latest/admin/session-property-managers.html).

Leverages the `file-group-provider` and `resource-groups` module to define
various user groups and resource management logic within the system.

## Usage

    # Get into the container and connect as a user tied to a group
    minitrino --env STARBURST_VER=<ver> provision --module session-property-manager
    docker exec -it trino bash 
    trino-cli --user admin
    trino> select 1;

The resource groups will apply to all users, with varying weights and priorities
assigned to certain user groups. Session properties applied to queries can be
viewed on the query details through the Trino web UI at `localhost:8080/ui/`.

The session property JSON file is mounted to Trino as a volume and can be
viewed/edited within the container:

    docker exec -it trino bash 
    vi /etc/starburst/session-property.json

Alternatively, it can be edited directly in the library:

    lib/modules/admin/session-property-manager/resources/trino/session-property.json
