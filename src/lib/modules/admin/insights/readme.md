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

## Persistent Storage

This module uses named volumes to persist Postgres data:

    volumes:
      postgres-insights-data:
        labels:
          - com.starburst.tests=minitrino
          - com.starburst.tests.module.insights=admin-insights

The user-facing implication is that the data in Postgres is retained even after
shutting down and/or removing the environment's containers. Minitrino issues a
warning about this whenever a module with named volumes is deployed––be sure to
look out for these warnings:

    [w]  Module '<module>' has persistent volumes associated with it. To delete these volumes, remember to run `minitrino remove --volumes`.

To remove these volumes, run:

    minitrino -v remove --volumes --label com.starburst.tests.module.insights=admin-insights

Or, remove them directly using the Docker CLI:

    docker volume rm minitrino_postgres-insights-data
