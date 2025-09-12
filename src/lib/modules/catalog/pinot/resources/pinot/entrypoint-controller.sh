#!/usr/bin/env bash

set -euxo pipefail

# Start Pinot controller in background, as the main process
./bin/pinot-admin.sh "$@" &
CONTROLLER_PID=$!

# Wait for the controller to be healthy before running bootstrap
for _ in {1..36}; do
  if curl -s http://localhost:9000/health | grep -q OK; then
    echo "Pinot controller is healthy."
    break
  fi
  echo "Waiting for Pinot controller to be healthy..."
  sleep 5
done

# Run the bootstrap script
if [ -x /bootstrap.sh ]; then
  /bootstrap.sh
else
  echo "Bootstrap script not found or not executable!"
  exit 1
fi

# Wait for the Pinot controller process to exit
wait ${CONTROLLER_PID}
