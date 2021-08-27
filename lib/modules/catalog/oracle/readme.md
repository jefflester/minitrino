# Oracle Connector Module

This module provisions a standalone Oracle service.

## Usage

You will want to use the `trino` schema within the `oracle` catalog.
Additionally, the Oracle server takes some time to become available after the
container boots up. If you see an `Unable to start the Universal Connection
Pool` error, wait 1-2 minutes and try querying Oracle again.

    # Login with the Docker Hub account used to "purchase" the image
    echo "your-password" | docker login -u <user> --password-stdindocker
    minitrino --env STARBURST_VER=<ver> provision --module oracle
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from oracle;
    trino> create table oracle.trino.test (a int);

## Image Pull Notes

To pull this image, you will need to:

- Create a Docker Hub account and then "purchase" the [developer-tier
  image](https://hub.docker.com/_/oracle-database-enterprise-edition).
- Authenticate to your Docker Hub account via the Docker CLI (see `docker login
  --help` for more information)
