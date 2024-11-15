# Insights Module  

This module configures and deploys the necessary components for
[Insights](https://docs.starburst.io/latest/insights/configuration.html)
features in the SEP web UI, including the required [backend
service](https://docs.starburst.io/latest/admin/backend-service.html) database
which persists the data to provide information needed for the Insights UI.

## Usage

The backend service database can be queried directly, as it is exposed as a
catalog. For example:

    minitrino --env STARBURST_VER=<ver> provision --module insights
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from backend_svc;

## Accessing Insights Web UI

Open a web browser, navigate to
[https://localhost:8080](https://localhost:8080), and log in with any user. The
Insights UI should be enabled.
