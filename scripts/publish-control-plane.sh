#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${GITHUB_REPOSITORY:?repository required}"
: "${GITHUB_SHA:?commit required}"
[[ "$GITHUB_REPOSITORY" == skizzay/slickflow && "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]] || {
  echo 'Publication requires skizzay/slickflow and a full lowercase commit SHA' >&2; exit 1;
}
[[ $(git rev-parse HEAD) == "$GITHUB_SHA" ]] || {
  echo 'Publication checkout does not match the selected commit' >&2; exit 1;
}
case "${GITHUB_EVENT_NAME:-}:${GITHUB_REF:-}" in
  push:refs/heads/main|workflow_dispatch:refs/heads/main) ;;
  *) echo 'Publication requires a push or manual dispatch on refs/heads/main' >&2; exit 1 ;;
esac
# Check the source before registry authentication and again before pushing.
if [[ ${1:-} == --check-source ]]; then
  exit 0
fi
: "${GITHUB_RUN_ID:?pipeline run required}"
: "${GITHUB_STEP_SUMMARY:?pipeline summary path required}"
: "${SLICKFLOW_PUBLISH_ARCH:?native architecture required}"
case "$SLICKFLOW_PUBLISH_ARCH" in amd64|arm64) ;; *)
  echo 'Publication supports only native amd64 or arm64' >&2; exit 1 ;;
esac
# Validate both before publishing either. Tags aid discovery; consumers use digests.
for target in runtime migration; do
  image="slickflow-$target:$GITHUB_SHA-$SLICKFLOW_PUBLISH_ARCH"
  [[ $(docker image inspect "$image" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}') == "$GITHUB_SHA" ]]
  [[ $(docker image inspect "$image" --format '{{.Architecture}} {{.Config.User}}') == "$SLICKFLOW_PUBLISH_ARCH 10001:10001" ]]
done
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
for target in runtime migration; do
  repository="ghcr.io/$GITHUB_REPOSITORY-$target"
  image="$repository:$GITHUB_SHA-$SLICKFLOW_PUBLISH_ARCH"
  docker tag "slickflow-$target:$GITHUB_SHA-$SLICKFLOW_PUBLISH_ARCH" "$image"
  docker push "$image"
  digest=$(docker image inspect "$image" --format '{{json .RepoDigests}}' | \
    python3 -c 'import json,re,sys; prefix=sys.argv[1]+"@"; matches=[x for x in json.load(sys.stdin) if x.startswith(prefix) and re.fullmatch(r"sha256:[0-9a-f]{64}",x[len(prefix):])]; assert len(matches)==1; print(matches[0])' "$repository")
  printf '%s %s\n' "$target" "$digest" >> "$manifest"
done
python3 - "$manifest" <<'PY'
import json, os, pathlib, sys
e=os.environ
record={
    'revision':e['GITHUB_SHA'], 'architecture':e['SLICKFLOW_PUBLISH_ARCH'],
    'run_url':f"https://github.com/{e['GITHUB_REPOSITORY']}/actions/runs/{e['GITHUB_RUN_ID']}",
    'run_attempt':e.get('GITHUB_RUN_ATTEMPT','1'),
    'images':dict(line.split() for line in pathlib.Path(sys.argv[1]).read_text().splitlines()),
}
path=pathlib.Path(f"provenance-{record['architecture']}.json")
path.write_text(json.dumps(record,indent=2)+'\n')
with open(e['GITHUB_STEP_SUMMARY'],'a') as summary:
    summary.write('### Verified control-plane artifacts\n\n```json\n'+path.read_text()+'```\n')
PY
