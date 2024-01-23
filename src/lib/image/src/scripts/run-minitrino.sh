#!/usr/bin/env bash

# This script exists because the Java PID for the SEP service tends to stick
# around for a second or two when restarting a container. This circumvents that
# issue by retrying the start command a few times before giving up.

max_attempts=5

# Attempt to start the service
for ((attempt=1; attempt<=max_attempts; attempt++)); do
    /usr/lib/starburst/bin/run-starburst && break

    # If the service failed to start, wait for a second before trying again
    echo "Startup attempt $attempt failed, retrying in 1 second..."
    sleep 1
done

# If the service failed to start after max_attempts, exit with a non-zero status code
if ((attempt > max_attempts)); then
    echo "Service failed to start after $max_attempts attempts, exiting..."
    exit 1
fi
