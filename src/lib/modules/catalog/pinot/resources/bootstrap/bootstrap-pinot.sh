#!/usr/bin/env bash

set -euxo pipefail

echo "Checking component statuses..."
check_health() {
  local url=$1
  local retries=20
  local wait=5

  for ((i=0; i<retries; i++)); do
    response=$(curl -s "$url")
    if [[ "$response" == "OK" ]]; then
      echo "Component at $url is ready."
      return 0
    else
      echo "Waiting for component at $url to be ready..."
      sleep $wait
    fi
  done

  echo "Component at $url failed to respond with 'ok' after $((retries * wait)) seconds."
  return 1
}

# Check each component
check_health http://pinot-controller:9000/health || exit 1  # Controller
check_health http://pinot-broker:8099/health || exit 1  # Broker

echo "All components are up and running."

echo "Loading Pinot sample data..."
cd /opt/pinot/

# Baseball
bin/pinot-admin.sh AddTable \
  -schemaFile /opt/pinot/examples/batch/baseballStats/baseballStats_schema.json \
  -tableConfigFile /opt/pinot/examples/batch/baseballStats/baseballStats_offline_table_config.json \
  -controllerHost localhost \
  -controllerPort 9000 \
  -exec

bin/pinot-admin.sh LaunchDataIngestionJob \
  -jobSpecFile /opt/pinot/examples/batch/baseballStats/ingestionJobSpec.yaml

bin/pinot-admin.sh AddTable \
  -schemaFile /opt/pinot/examples/batch/dimBaseballTeams/dimBaseballTeams_schema.json \
  -tableConfigFile /opt/pinot/examples/batch/dimBaseballTeams/dimBaseballTeams_offline_table_config.json \
  -controllerHost localhost \
  -controllerPort 9000 \
  -exec

bin/pinot-admin.sh LaunchDataIngestionJob \
  -jobSpecFile /opt/pinot/examples/batch/dimBaseballTeams/ingestionJobSpec.yaml

# GitHub
bin/pinot-admin.sh AddTable \
  -schemaFile /opt/pinot/examples/batch/githubEvents/githubEvents_schema.json \
  -tableConfigFile /opt/pinot/examples/batch/githubEvents/githubEvents_offline_table_config.json \
  -controllerHost localhost \
  -controllerPort 9000 \
  -exec

bin/pinot-admin.sh LaunchDataIngestionJob \
  -jobSpecFile /opt/pinot/examples/batch/githubEvents/ingestionJobSpec.yaml

bin/pinot-admin.sh AddTable \
  -schemaFile /opt/pinot/examples/batch/githubComplexTypeEvents/githubComplexTypeEvents_schema.json \
  -tableConfigFile /opt/pinot/examples/batch/githubComplexTypeEvents/githubComplexTypeEvents_offline_table_config.json \
  -controllerHost localhost \
  -controllerPort 9000 \
  -exec

bin/pinot-admin.sh LaunchDataIngestionJob \
  -jobSpecFile /opt/pinot/examples/batch/githubComplexTypeEvents/ingestionJobSpec.yaml
