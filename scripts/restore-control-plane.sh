#!/usr/bin/env bash
set -euo pipefail
: "${PGSERVICE:?select a private libpq service for the isolated restore target}"
: "${SLICKFLOW_BACKUP_DIR:?select one private backup directory}"
[[ -f "$SLICKFLOW_BACKUP_DIR/database.dump" && -f "$SLICKFLOW_BACKUP_DIR/SHA256SUMS" ]] || {
  echo 'Backup and checksum manifest required' >&2; exit 1;
}
# No create, drop, clean or production overwrite; operator supplies a NEW target.
database=$(psql -XAt -v ON_ERROR_STOP=1 -c 'SELECT current_database()')
[[ "$database" =~ ^slickflow_restore_[a-z0-9_]+$ ]] || {
  echo 'Restore requires an isolated slickflow_restore_* database' >&2; exit 1;
}
[[ $(psql -XAt -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp%'") == 0 ]] || {
  echo 'Restore target must have no user relations' >&2; exit 1;
}
(cd "$SLICKFLOW_BACKUP_DIR" && sha256sum --check --status SHA256SUMS)
pg_restore --exit-on-error --single-transaction --dbname="service=$PGSERVICE" "$SLICKFLOW_BACKUP_DIR/database.dump"
psql -X -v ON_ERROR_STOP=1 -c 'SELECT count(*) AS successful_migrations FROM slickflow.flyway_schema_history WHERE success' \
  -c 'SELECT count(*) AS registered_definitions FROM slickflow.workflow_definition'
echo 'Isolated restore complete; verify expected data and runtime health before accepting recovery.'
