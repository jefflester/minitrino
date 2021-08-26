# Event Logger Module

This module configures and deploys the necessary components for the [Starburst
event logger](https://docs.starburst.io/latest/security/event-logger.html). This
feature logs query history and persists the data to an external database. This
is a prerequisite for Starburst Insights query history.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module event-logger
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from postgres_event_logger;
