# Insights Module  

This module configures and deploys the necessary components for [Insights](https://docs.starburst.io/latest/insights/configuration.html) features in the SEP web UI, including the required [Query Logger](https://docs.starburst.io/latest/admin/query-logger.html) database which persists the data to provide information needed for Insights features.  

This module is a prerequisite for Built-in access control (BIAC).  

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module insights
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from postgres_query_logger;

## Accessing Insights Web UI
Open a web browser and go to [https://localhost:8080](https://localhost:8080) and log in with a user that is authorized to access insights.  

Note: `insights.authorized-*` properties cannot be used in conjunction with SEP's built-in access control properties (`starburst.access-control`). If you need to access Insights features in the UI without enabling BIAC, you will need to uncomment the `insights.authorized-users=.*` property in the coordinator's `/etc/starburst/config.properties` file.  