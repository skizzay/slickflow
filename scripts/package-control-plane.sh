#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
revision=$(git rev-parse --verify "${1:-HEAD}^{commit}")
platform=${2:-linux/arm64}
case "$platform" in linux/arm64|linux/amd64) ;; *) echo 'Supported platforms: linux/arm64, linux/amd64' >&2; exit 1 ;; esac
case "$(docker info --format '{{.Architecture}}')" in
  x86_64|amd64) builder_platform=linux/amd64 ;;
  aarch64|arm64) builder_platform=linux/arm64 ;;
  *) echo 'Unsupported builder architecture' >&2; exit 1 ;;
esac
context=$(mktemp -d)
trap 'rm -rf "$context"' EXIT
# Only committed source enters the build: no working-tree secrets or local JARs.
git archive "$revision" | tar -x -C "$context"
suffix=${platform#linux/}
for target in migration runtime; do
  docker build --platform "$platform" --target "$target" \
    --build-arg "BUILD_PLATFORM=$builder_platform" \
    --build-arg "SOURCE_REVISION=$revision" \
    -f "$context/packaging/control-plane/Dockerfile" \
    -t "slickflow-$target:$revision-$suffix" "$context"
  # Local content IDs are immutable. Registry manifest digests are added by #112.
  docker image inspect "slickflow-$target:$revision-$suffix" \
    --format '{{.Id}} {{.Os}}/{{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}}'
done
