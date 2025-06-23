# Session Property Manager Module

A module which implements Trino's file-based [session property
manager](https://docs.starburst.io/latest/admin/session-property-managers.html).

Leverages the `file-group-provider` and `resource-groups` module to define
various user groups and resource management logic within the system.

## Usage

```sh
minitrino -v provision -m session-property-manager
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m session-property-manager

# Get into the container and connect as a user tied to a group
docker exec -it minitrino bash 
trino-cli --user admin

trino> SELECT 1;
```

The resource groups will apply to all users, with varying weights and priorities
assigned to certain user groups. Session properties applied to queries can be
viewed on the query details through the Trino web UI at `localhost:8080/ui/`.

The session property JSON file is mounted to the cluster as a volume and can be
viewed/edited within the container:

```sh
docker exec -it minitrino bash 
vi /etc/"${CLUSTER_DIST}"/session-property.json
```

Alternatively, it can be edited directly in the library:

```sh
lib/modules/admin/session-property-manager/resources/cluster/session-property.json
```
