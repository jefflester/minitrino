# Oracle Connector Module

This module provisions a standalone Oracle service.

## Usage

    # Login with the Docker Hub account used to "purchase" the image
    echo "your-password" | docker login -u <user> --password-stdindocker
    minitrino --env STARBURST_VER=<ver> provision --module oracle
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from oracle;

## Image Pull Notes

To pull this image, you will need to:

- Create a Docker Hub account and then "purchase" the [developer-tier
  image](https://hub.docker.com/_/oracle-database-enterprise-edition).
- Authenticate to your Docker Hub account via the Docker CLI (see `docker login
  --help` for more information)
