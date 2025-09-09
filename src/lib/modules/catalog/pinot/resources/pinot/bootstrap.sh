#!/usr/bin/env bash

set -euxo pipefail

echo "Checking component statuses..."
check_health() {
  local url=$1
  local retries=36
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

  echo "Component at $url failed to respond with 'OK' after $((retries * wait)) seconds."
  return 1
}

# Check each component
check_health http://pinot-controller:9000/health || exit 1  # Controller
check_health http://pinot-broker:8099/health || exit 1  # Broker

echo "All components are up and running."

echo "Loading Pinot sample data..."
cd /opt/pinot/

load_table_if_not_exists() {
  local schema_file=$1
  local table_config_file=$2
  local table_name
  table_name=$(basename "$table_config_file" | cut -d_ -f1)

  # Check if the table already exists
  if curl -s http://pinot-controller:9000/tables | grep -q "\"$table_name\""; then
    echo "Table '$table_name' already exists. Skipping creation."
  else
    echo "Creating table '$table_name'..."
    bin/pinot-admin.sh AddTable \
      -schemaFile "$schema_file" \
      -tableConfigFile "$table_config_file" \
      -controllerHost localhost \
      -controllerPort 9000 \
      -exec
  fi
}

launch_job_if_not_loaded() {
  local job_spec_file=$1
  local table_name
  table_name=$(basename "$job_spec_file" | cut -d_ -f1)

  # Check if the table already has data
  row_count=$(curl -s http://pinot-broker:8099/query -X POST -d "SELECT COUNT(*) FROM $table_name" | grep -o '"rows":[[][0-9]*' | awk -F':' '{print $2}' || echo 0)
  if [[ $row_count -gt 0 ]]; then
    echo "Table '$table_name' already contains data. Skipping ingestion."
  else
    echo "Launching ingestion job for '$table_name'..."
    bin/pinot-admin.sh LaunchDataIngestionJob -jobSpecFile "$job_spec_file"
  fi
}

# Baseball
load_table_if_not_exists \
  /opt/pinot/examples/batch/baseballStats/baseballStats_schema.json \
  /opt/pinot/examples/batch/baseballStats/baseballStats_offline_table_config.json

launch_job_if_not_loaded /opt/pinot/examples/batch/baseballStats/ingestionJobSpec.yaml

load_table_if_not_exists \
  /opt/pinot/examples/batch/dimBaseballTeams/dimBaseballTeams_schema.json \
  /opt/pinot/examples/batch/dimBaseballTeams/dimBaseballTeams_offline_table_config.json

launch_job_if_not_loaded /opt/pinot/examples/batch/dimBaseballTeams/ingestionJobSpec.yaml

# GitHub
load_table_if_not_exists \
  /opt/pinot/examples/batch/githubEvents/githubEvents_schema.json \
  /opt/pinot/examples/batch/githubEvents/githubEvents_offline_table_config.json

launch_job_if_not_loaded /opt/pinot/examples/batch/githubEvents/ingestionJobSpec.yaml

load_table_if_not_exists \
  /opt/pinot/examples/batch/githubComplexTypeEvents/githubComplexTypeEvents_schema.json \
  /opt/pinot/examples/batch/githubComplexTypeEvents/githubComplexTypeEvents_offline_table_config.json

launch_job_if_not_loaded /opt/pinot/examples/batch/githubComplexTypeEvents/ingestionJobSpec.yaml
