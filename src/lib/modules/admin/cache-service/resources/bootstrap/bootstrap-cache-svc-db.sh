#!/bin/sh

export PGPASSWORD="${POSTGRES_PASSWORD}"
psql -U "${POSTGRES_USER}" -d postgres \
  -tc "SELECT 1 FROM pg_database WHERE datname = 'cachesvc';" | grep -q 1 || \
  psql -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE cachesvc;"
