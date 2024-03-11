# Redis Connector Module

This module provisions a standalone Redis Enterprise service. Redis services can
be accessed on the following endpoints:

- RedisInsight: `https://localhost:7443` (port `8443` is used within the
  container network)
- Redis API: `https://localhost:9443`
- Redis database client connections: `https://localhost:12000`

A cluster is created and joined, and a sample database is also created via the
bootstrap script.

To use the Redis UI, navigate to `https://localhost:7443`, accept the privacy
warning to bypass the self-signed certificate warning in your browser, and
authenticate to the cluster with:

- Email: `admin@redis.com`
- Password: `changeit`

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module redis
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from redis;
