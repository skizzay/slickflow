#!/usr/bin/env bash
set -euo pipefail
# Read-only checks; never alter kernel settings, pull images or start services.
python3 - <<'PY'
import os, re, stat
from urllib.parse import urlsplit, parse_qs

def require(ok, message):
    if not ok:
        raise SystemExit(message)
for key in ('SLICKFLOW_RUNTIME_IMAGE', 'SLICKFLOW_MIGRATION_IMAGE'):
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
for key in ('SLICKFLOW_RUNTIME_PASSWORD_FILE','SLICKFLOW_MIGRATION_PASSWORD_FILE'):
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
require(re.fullmatch(r'[1-9][0-9]*[mg]',os.getenv('SLICKFLOW_MIGRATION_MEMORY','')),
        'Approved migration memory budget required, such as an integer followed by m or g')
PY
[[ $(docker info --format '{{.MemoryLimit}}') == true ]] || {
  echo 'Docker memory-limit enforcement is unavailable; reconcile before starting hosting' >&2; exit 1;
}
[[ $(docker info --format '{{.Architecture}}') =~ ^(aarch64|arm64)$ ]] || {
  echo 'Approved hosting target requires ARM64 Docker' >&2; exit 1;
}
revision=
for image in "$SLICKFLOW_RUNTIME_IMAGE" "$SLICKFLOW_MIGRATION_IMAGE"; do
  current=$(docker image inspect "$image" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')
  [[ "$current" =~ ^[0-9a-f]{40}$ && ( -z "$revision" || "$current" == "$revision" ) ]] || {
    echo 'Paired image source revisions must match' >&2; exit 1;
  }
  [[ $(docker image inspect "$image" --format '{{.Architecture}} {{.Config.User}}') == 'arm64 10001:10001' ]] || {
    echo 'Hosting images must be ARM64 and non-root' >&2; exit 1;
  }
  revision=$current
done
docker compose -f "$(dirname "$0")/../deployment/control-plane/compose.yaml" config --quiet
echo 'Local hosting configuration checks passed; network/secret-store/reboot evidence is still required.'
