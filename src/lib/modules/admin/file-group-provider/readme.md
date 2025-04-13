# File Group Provider Module

A module which utilizes Trino's [file-based group
provider](https://docs.starburst.io/latest/security/group-file.html).

## Usage

```sh
minitrino -v provision -m file-group-provider
# Or specify cluster version
minitrino -v -e CLUSTER_VER=${version} provision -m file-group-provider

# View group definitions
docker exec minitrino sh -c 'cat /etc/${CLUSTER_DIST}/groups.txt'

# Get into the container and connect as a user tied to a group
docker exec -it minitrino bash 
trino-cli --user admin

trino> SHOW SCHEMAS FROM tpch;
```

You will need to supply a username to the Trino CLI in order to map to a group
(see `lib/modules/security/file-access-control/resources/cluster/groups.txt` for
which users belong to which groups). Example:

```sh
trino-cli --user admin # maps to group clusteradmins
```
