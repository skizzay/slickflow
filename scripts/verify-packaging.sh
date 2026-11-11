#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SLICKFLOW_RUNTIME_IMAGE:?set immutable runtime image ID}"
: "${SLICKFLOW_MIGRATION_IMAGE:?set immutable migration image ID}"
for image in "$SLICKFLOW_RUNTIME_IMAGE" "$SLICKFLOW_MIGRATION_IMAGE"; do
  [[ "$image" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "Use immutable local image IDs" >&2; exit 1; }
done
export SLICKFLOW_RUNTIME_IMAGE SLICKFLOW_MIGRATION_IMAGE
export SLICKFLOW_TEST_PASSWORD
SLICKFLOW_TEST_PASSWORD=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
project="slickflow-package-${RANDOM}-$$"
compose=(docker compose -f packaging/control-plane/compose.verify.yaml -p "$project")
cleanup() { "${compose[@]}" down --volumes --remove-orphans >/dev/null; }
trap cleanup EXIT
runtime_revision=$(docker image inspect "$SLICKFLOW_RUNTIME_IMAGE" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')
migration_revision=$(docker image inspect "$SLICKFLOW_MIGRATION_IMAGE" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')
if [[ ! "$runtime_revision" =~ ^[0-9a-f]{40}$ || "$runtime_revision" != "$migration_revision" ]]; then
  echo "Image revision labels must match and contain a full 40-character commit SHA" >&2
  exit 1
fi
for image in "$SLICKFLOW_RUNTIME_IMAGE" "$SLICKFLOW_MIGRATION_IMAGE"; do
  if [[ $(docker image inspect "$image" --format '{{.Config.User}}') != 10001:10001 ]]; then
    echo "Both images must run as UID/GID 10001:10001" >&2
    exit 1
  fi
  docker run --rm --entrypoint sh "$image" -c 'test ! -e /build && ! command -v mvn && ! command -v javac'
done
"${compose[@]}" up -d --wait db
# PostgreSQL 18 uses a versioned directory within the declared parent volume.
data_directory=$("${compose[@]}" exec -T db psql -At -U migrator -d slickflow -c 'SHOW data_directory')
if [[ "$data_directory" != /var/lib/postgresql/18/docker ]]; then
  echo "Unexpected PostgreSQL 18 data directory for the pinned smoke fixture" >&2
  exit 1
fi
"${compose[@]}" run --rm migration
# A second run must validate/no-op without destructive repair.
"${compose[@]}" run --rm migration
"${compose[@]}" exec -T db psql -v ON_ERROR_STOP=1 -U migrator -d slickflow <<'SQL'
-- Reuse the random disposable password without printing it or passing it in argv.
\getenv fixture_password POSTGRES_PASSWORD
CREATE ROLE runtime LOGIN PASSWORD :'fixture_password';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE slickflow TO runtime;
GRANT USAGE ON SCHEMA slickflow, flowable TO runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA slickflow, flowable TO runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA slickflow, flowable TO runtime;
SQL
"${compose[@]}" up -d runtime
port=$("${compose[@]}" port runtime 8080)
healthy=false
for ((attempt=0; attempt<120; attempt++)); do
  if curl --fail --silent "http://$port/actuator/health" | grep -q '"status":"UP"'; then healthy=true; break; fi
  sleep 1
done
[[ "$healthy" == true ]]
# Confirm successful connection/read as the intended role before testing denial.
runtime_psql() {
  PGPASSWORD="$SLICKFLOW_TEST_PASSWORD" "${compose[@]}" exec -T -e PGPASSWORD db \
    psql -h 127.0.0.1 -U runtime -d slickflow -v ON_ERROR_STOP=1 "$@"
}
runtime_identity=$(runtime_psql -At -c 'SELECT current_user')
if [[ "$runtime_identity" != runtime ]]; then
  echo "Permission checks must connect as the runtime database role" >&2
  exit 1
fi
runtime_psql -c 'SELECT count(*) FROM slickflow.repository' >/dev/null
# Catch only permission denial. Connection failures or unrelated SQL errors fail.
runtime_psql >/dev/null <<'SQL'
DO $$
BEGIN
  CREATE TABLE slickflow.forbidden_fixture(id integer);
  RAISE EXCEPTION 'Runtime role unexpectedly has DDL access';
EXCEPTION WHEN insufficient_privilege THEN
  NULL;
END
$$;
SQL
status=$(curl --silent --output /dev/null --write-out '%{http_code}' "http://$port/not-exposed")
[[ "$status" == 401 || "$status" == 403 ]]
echo "PASS: migration, replay, DML-only runtime health and route denial ($runtime_revision)"
