#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${PGSERVICE:?select a private libpq service for SlickFlow backup}"
: "${SLICKFLOW_BACKUP_DIR:?private backup directory required}"
[[ -d "$SLICKFLOW_BACKUP_DIR" ]] || { echo 'Backup directory must already exist' >&2; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd -P)
directory=$(realpath "$SLICKFLOW_BACKUP_DIR")
[[ "$directory/" != "$root/"* ]] || { echo 'Backups must be outside the checkout' >&2; exit 1; }
[[ $(psql -XAt -v ON_ERROR_STOP=1 -c 'SELECT current_database()') == slickflow ]] || {
  echo 'Backup service must select the dedicated slickflow database' >&2; exit 1;
}
work=$(mktemp -d "$directory/.backup-XXXXXXXX")
trap 'rm -rf "$work"' EXIT
pg_dump --format=custom --file="$work/database.dump"
pg_restore --list "$work/database.dump" >/dev/null
(cd "$work" && sha256sum database.dump > SHA256SUMS)
# Unique directory prevents overwriting earlier evidence; files stay private.
name="slickflow-$(date -u +%Y%m%dT%H%M%SZ)-${work##*-}"
mv "$work" "$directory/$name"
trap - EXIT
echo "Backup complete: $name (database.dump and SHA256SUMS)"
