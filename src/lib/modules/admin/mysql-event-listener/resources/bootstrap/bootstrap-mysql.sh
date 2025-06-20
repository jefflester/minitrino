#!/usr/bin/env bash

MAX_ATTEMPTS=60
for (( ATTEMPTS=1; ATTEMPTS<=MAX_ATTEMPTS; ATTEMPTS++ ))
do
   if mysql -ptrinoRocks15 -e "GRANT ALL PRIVILEGES ON *.* TO 'admin';"; then
      break
   fi
   sleep 1
done

echo "Creating 'event_listener' database..."
mysql -ptrinoRocks15 -e "CREATE DATABASE event_listener;"
