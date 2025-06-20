#!/usr/bin/env bash

MAX_ATTEMPTS=60
for (( ATTEMPTS=1; ATTEMPTS<=MAX_ATTEMPTS; ATTEMPTS++ ))
do
   # Check if the admin user already has privileges
   if mysql -ptrinoRocks15 -e "SHOW GRANTS FOR 'admin';" \
      | grep -q "GRANT ALL PRIVILEGES ON *.* TO 'admin'"
   then
      echo "Privileges already granted to 'admin'. Skipping privilege grant."
      break
   fi

   # Grant privileges if they are not already granted
   if mysql -ptrinoRocks15 -e "GRANT ALL PRIVILEGES ON *.* TO 'admin';"
   then
      break
   fi
   sleep 1
done

echo "Ensuring 'minitrino' database exists..."
mysql -ptrinoRocks15 -e "CREATE DATABASE IF NOT EXISTS minitrino;"
