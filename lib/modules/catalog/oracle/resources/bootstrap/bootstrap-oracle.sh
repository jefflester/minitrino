#!/usr/bin/env bash

set -ex

function health_check() {
    su - oracle -c "source /home/oracle/.bashrc; sqlplus sys/Oradoc_db1 as sysdba @/tmp/health-check.sql"
}

function create_user() {
    su - oracle -c "source /home/oracle/.bashrc; sqlplus sys/Oradoc_db1 as sysdba @/tmp/create-user.sql"
}

function grant_privileges() {
    su - oracle -c "source /home/oracle/.bashrc; sqlplus sys/Oradoc_db1 as sysdba @/tmp/grant-privileges.sql"
}

echo "Creating health check SQL script..."
cat <<EOT >> /tmp/health-check.sql
SELECT INSTANCE_NAME, STATUS, DATABASE_STATUS FROM V\$INSTANCE;
exit;
EOT

echo "Creating user-creation SQL script..."
cat <<EOT >> /tmp/create-user.sql
ALTER SESSION SET "_ORACLE_SCRIPT"=true;
CREATE USER trino IDENTIFIED BY trinoRocks15;
exit;
EOT

echo "Creating user-privilege SQL script..."
cat <<EOT >> /tmp/grant-privileges.sql
ALTER SESSION SET "_ORACLE_SCRIPT"=true;
GRANT CONNECT, RESOURCE, DBA TO trino;
GRANT CREATE SESSION, CREATE TABLE TO trino;
GRANT UNLIMITED TABLESPACE TO trino;
GRANT ALL PRIVILEGES TO trino;
exit;
EOT

echo "Performing health checks..."
COUNTER=0 && set +e
while [[ "${COUNTER}" -lt 121 ]]; do 
    if health_check | grep -q "trinosid\|OPEN\|ACTIVE"; then
        break
    elif [[ "${COUNTER}" == 121 ]]; then
        echo "Database is not up and running and timed out after approx. 2 minutes. Exiting"
        exit 1
    else 
        sleep 1
        ((COUNTER++))
    fi
done

echo "Creating user..."
COUNTER=0 && set +e
while [[ "${COUNTER}" -lt 61 ]]; do
    if create_user | grep -q "ERROR"; then
        sleep 1
        ((COUNTER++))
    elif [[ "${COUNTER}" == 61 ]]; then
        echo "User creation failed after approx. 1 minute. Exiting"
        exit 1
    else
        break
    fi
done

echo "Granting user privileges..."
COUNTER=0 && set +e
while [[ "${COUNTER}" -lt 61 ]]; do
    if grant_privileges | grep -q "ERROR"; then
        sleep 1
        ((COUNTER++))
    elif [[ "${COUNTER}" == 61 ]]; then
        echo "Privilege grant failed after approx. 1 minute. Exiting"
        exit 1
    else
        break
    fi
done
