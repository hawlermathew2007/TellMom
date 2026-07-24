#!/bin/sh
set -e
set -a
source ./.env
set +a

export PGPASSWORD="$POSTGRES_PASSWORD"

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -h localhost <<-EOSQL
SELECT 'CREATE DATABASE backend_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'backend_db')\gexec

SELECT 'CREATE DATABASE proxy_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'proxy_db')\gexec
EOSQL
