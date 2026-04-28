#!/usr/bin/env bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'bf_user') THEN
      CREATE ROLE bf_user LOGIN PASSWORD 'bf_password';
   END IF;
END
$$;
SQL

for db in borderflow_depot borderflow_border borderflow_port borderflow_destination; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
SELECT 'CREATE DATABASE ${db} OWNER bf_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${db}')\gexec
SQL

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${db}" -f /docker-entrypoint-initdb.d/schema.sql
done
