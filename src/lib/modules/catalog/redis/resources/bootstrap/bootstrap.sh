#!/usr/bin/env bash

set -euxo pipefail

# Wait for Redis API to become available
until $(curl -v -k -s -o /dev/null -w "%{http_code}" https://localhost:9443 | awk '{exit $1>=500?1:0}'); do
  printf '.'
  sleep 5
done

# Create Redis cluster
curl -v -k -X POST -H "Content-Type: application/json" -d '{
  "action": "create_cluster",
  "cluster": {
    "nodes": [],
    "name": "cluster.local"
  },
  "node": {
    "paths": {
      "persistent_path": "/var/opt/redislabs/persist",
      "ephemeral_path": "/var/opt/redislabs/tmp"
    },
    "identity": {
      "addr":"'"$(hostname -i)"'"
    }
  },
  "credentials": {
    "username": "admin@redis.com",
    "password": "changeit"
  }
}' https://localhost:9443/v1/bootstrap/create_cluster

# Wait for cluster creation to complete
until $(curl -k -u "admin@redis.com:changeit" --output /dev/null --silent --head --fail https://localhost:9443/v1/cluster); do
  printf '.'
  sleep 5
done

# Join Redis cluster
curl -v -k -X POST -H "Content-Type: application/json" -d '{
  "action": "join_cluster",
  "cluster": {
    "nodes": [],
    "name": "cluster.local"
  },
  "node": {
    "identity": {
      "addr":"'"$(hostname -i)"'"
    }
  },
  "credentials": {
    "username": "my_username",
    "password": "my_password"
  }
}' https://localhost:9443/v1/bootstrap/join_cluster

# Create Redis database
curl -v -k -X POST -u "admin@redis.com:changeit" -H "Content-Type: application/json" -d '{
  "name": "sample",
  "type": "redis",
  "memory_size": 1000000000,
  "port": 12000
}' https://localhost:9443/v1/bdbs
