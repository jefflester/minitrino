#!/usr/bin/env bash

MAX_ATTEMPTS=60
for (( ATTEMPTS=1; ATTEMPTS<=MAX_ATTEMPTS; ATTEMPTS++ ))
do
   mysql -ptrinoRocks15 -e "GRANT ALL PRIVILEGES ON *.* TO 'admin';"
   if [ $? == 0 ]; then
      break
   fi
   sleep 1
done

echo "Creating 'minitrino' database..."
mysql -ptrinoRocks15 -e "CREATE DATABASE minitrino;"
