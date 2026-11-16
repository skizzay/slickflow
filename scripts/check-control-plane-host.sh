#!/usr/bin/env bash
set -euo pipefail
# Read-only checks; never alter kernel settings, pull images or start services.
role=${1:-runtime}
case "$role" in runtime|migration) ;; *) echo "Usage: $0 [runtime|migration]" >&2; exit 2 ;; esac
export SLICKFLOW_PREFLIGHT_ROLE="$role"
python3 - <<'PY'
import os, re, stat
from urllib.parse import urlsplit, parse_qs

def require(ok, message):
    if not ok:
        raise SystemExit(message)
role=os.environ['SLICKFLOW_PREFLIGHT_ROLE']
for key in ('SLICKFLOW_'+role.upper()+'_IMAGE',):
    require(re.fullmatch(r'(?:sha256:|[^\s]+@sha256:)[0-9a-f]{64}', os.getenv(key,'')),
            key + ' must be an immutable image ID or registry digest')
url=os.getenv('SLICKFLOW_DB_URL','')
require(url.startswith('jdbc:postgresql://'), 'A PostgreSQL JDBC URL is required')
u=urlsplit(url[5:]); q=parse_qs(u.query,keep_blank_values=True)
require(u.hostname and not u.username and not u.password and u.path=='/slickflow' and not u.fragment,
        'JDBC URL must select slickflow with no embedded credentials')
require(q.get('currentSchema')==['slickflow'] and q.get('sslmode')==['verify-full'] and
        q.get('sslrootcert')==['/run/trust/postgresql-ca.crt'] and
        not any(k.lower() in ('user','password','sslpassword') for k in q),
        'Require slickflow schema and verify-full TLS with the mounted CA; no URL credentials')
for key in ('SLICKFLOW_'+role.upper()+'_PASSWORD_FILE',):
    p=os.getenv(key,''); require(os.path.isabs(p) and os.path.isfile(p), key+' must select an existing private file')
    s=os.stat(p)
    require(not s.st_mode & 0o007 and
            ((s.st_uid==10001 and s.st_mode & stat.S_IRUSR) or (s.st_gid==10001 and s.st_mode & stat.S_IRGRP)),
            key+' must be private and readable by container UID/GID 10001')
require(os.path.isfile(os.getenv('SLICKFLOW_DB_CA_FILE','')), 'Existing database CA file required')
try:
    require(float(os.getenv('SLICKFLOW_CPU_LIMIT','0'))>0,'Approved CPU budget required')
except ValueError:
    raise SystemExit('Invalid CPU budget')
if role == 'migration':
    require(re.fullmatch(r'[1-9][0-9]*[mg]',os.getenv('SLICKFLOW_MIGRATION_MEMORY','')),
            'Approved migration memory budget required, such as an integer followed by m or g')
PY
[[ $(docker info --format '{{.MemoryLimit}}') == true ]] || {
  echo 'Docker memory-limit enforcement is unavailable; reconcile before starting hosting' >&2; exit 1;
}
host_arch=$(docker info --format '{{.Architecture}}')
case "$host_arch" in
  aarch64|arm64) image_arch=arm64 ;;
  x86_64|amd64) image_arch=amd64 ;;
  *) echo 'Unsupported Docker host architecture' >&2; exit 1 ;;
esac
if [[ "$role" == runtime && "$image_arch" != arm64 ]]; then
  echo 'Approved runtime target requires ARM64 Docker' >&2; exit 1
fi
if [[ "$role" == runtime ]]; then
  selected_image=$SLICKFLOW_RUNTIME_IMAGE
  recipe=compose.yaml
else
  selected_image=$SLICKFLOW_MIGRATION_IMAGE
  recipe=compose.migration.yaml
fi
revision=$(docker image inspect "$selected_image" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || {
  echo 'Image must identify its full source revision' >&2; exit 1;
}
[[ $(docker image inspect "$selected_image" --format '{{.Architecture}} {{.Config.User}}') == "$image_arch 10001:10001" ]] || {
  echo 'Image must match host architecture and use non-root UID/GID 10001' >&2; exit 1;
}
docker compose -f "$(dirname "$0")/../deployment/control-plane/$recipe" config --quiet
printf 'Local %s configuration checks passed at revision %s; verify matching remote revision and admin maintenance protocol before use.\n' "$role" "$revision"
