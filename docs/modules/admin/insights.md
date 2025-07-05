# Insights

Configure and deploy the necessary components for
[Insights](https://docs.starburst.io/latest/insights/configuration.html), which
includes the SEP UI and the required [backend
service](https://docs.starburst.io/latest/admin/backend-service.html) database.

## Usage

{{ starburst_license_warning }}

{{ persistent_storage_warning }}

Provision the module:

```sh
minitrino -e CLUSTER_VER=${version}-e provision -i starburst -m insights
```

{{ connect_trino_cli }}

The backend service database can be queried directly since it is exposed as a
catalog.

```sql
SHOW SCHEMAS FROM backend_svc;
```

## Accessing Insights Web UI

The UI is served by the coordinator at `http://localhost:8080`.
