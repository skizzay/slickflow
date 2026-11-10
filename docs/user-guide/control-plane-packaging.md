# Package the control plane

Implements [#110](https://github.com/skizzay/slickflow/issues/110) under
[epic #108](https://github.com/skizzay/slickflow/issues/108), after #109 merged
through [PR #116](https://github.com/skizzay/slickflow/pull/116).
The [deployment contract](../requirements/control-plane-deployment.md) owns target,
resource and authorization decisions. These commands build and verify local
artifacts; they neither publish images nor deploy to the shared database/Pi.

## Artifacts and source identity

Requirements: Git, Docker Engine with Buildx, network access to Docker Hub/Maven
Central, and (for smoke checks) Compose v2 and host curl. Run from repository root.
No local Java/Maven installation is required. Use a trusted Docker host; do not
mount its socket in the application or build container.

```sh
# Build the committed revision for the selected Pi architecture.
./scripts/package-control-plane.sh HEAD linux/arm64
# Optional native amd64 build for local verification.
./scripts/package-control-plane.sh HEAD linux/amd64
```

The script archives the exact commit into a temporary build context. Uncommitted
changes, ignored files, local environment files and existing build outputs do not
enter it. Commit intended source changes before building. Maven builds both Boot
JARs together with Java 21; final images use only the JRE and their respective JAR,
with UID/GID 10001, no source checkout, Maven or JDK. Builder and JRE multi-platform
base indexes are pinned by digest in the Dockerfile. Review/update these pins
explicitly for security maintenance; dependency versions remain owned by the POM.
Do not introduce real secrets into tracked resources or build arguments.

Two images are produced: `slickflow-runtime:COMMIT-ARCH` and
`slickflow-migration:COMMIT-ARCH`. Both carry the same full commit in
`org.opencontainers.image.revision`. The script prints immutable local image IDs,
platforms and source revisions. Tags are convenient mutable names; select content
IDs for execution. Registry manifest digests and publication belong to #112.
The source commit timestamp fixes Maven archive timestamps. Builds are repeatable
from committed source and pinned inputs; bit-identical images across builder
versions are not guaranteed. There are no automatic dependency upgrades.

The builder runs natively and produces architecture-independent Java bytecode.
Final JRE images follow the requested target platform. ARM64 build success alone
does not verify ARM64 execution: run smoke checks on an ARM64 host or a separately
configured emulator before deploying to the Pi. No emulator is installed by these
scripts. Packaging skips tests; run regression and smoke checks separately.

## Disposable PostgreSQL smoke check

```sh
revision=$(git rev-parse HEAD)
# Select the platform built above (arm64 on the target, amd64 on a native PC).
arch=amd64
export SLICKFLOW_RUNTIME_IMAGE=$(docker image inspect \
  "slickflow-runtime:$revision-$arch" --format '{{.Id}}')
export SLICKFLOW_MIGRATION_IMAGE=$(docker image inspect \
  "slickflow-migration:$revision-$arch" --format '{{.Id}}')
./scripts/verify-packaging.sh
./scripts/verify-bootstrap.sh
# Full suite against the selected production database version, in a NEW project.
COMPOSE_FILE=compose.yaml:packaging/control-plane/compose.regression18.yaml \
  ./scripts/verify-bootstrap.sh
```

Smoke verification creates a unique disposable Compose project with PostgreSQL
18.6, random temporary credentials and a volume mounted at `/var/lib/postgresql`
(the PostgreSQL 18 image layout). It runs migration twice, grants a separate
DML-only runtime identity, starts the runtime with a read-only root and writable
`/tmp`, verifies status-only health and denied unrelated routes, and confirms
runtime cannot create domain tables. Both images must have matching revision
labels and non-root identities. Cleanup removes only this project's containers
and volume. No Docker socket, source checkout or build-tool volume is mounted.
The runtime port is published on a randomly selected host-loopback port only.
The regular integration/architecture suite defaults to the development 17.11
baseline; the explicit override above runs the same suite on 18.6. It sets PGDATA
to the development volume target for its fresh disposable fixture only; it does
not upgrade an existing volume. The packaging smoke check uses the normal 18
image volume layout. Review both PostgreSQL digest pins together when updating.
These tests do not establish production TLS/HBA access or live webhook evidence.

## Run with external configuration

Select matching immutable image IDs or, after publication, registry digests from
the same source revision. Supply secrets through your deployment secret store;
these examples assume variables already exported securely. Never use test
credentials or the development Compose administrator against the shared service.

```sh
# Serialized maintenance: use the DDL migration identity in these variables.
docker run --rm \
  -e SLICKFLOW_DB_URL -e SLICKFLOW_DB_USER -e SLICKFLOW_DB_PASSWORD \
  -e SLICKFLOW_ENGINE_SCHEMA "$SLICKFLOW_MIGRATION_IMAGE"

# Switch exported credentials to the distinct runtime DML identity first.
# SLICKFLOW_CONFIG_DIR is an absolute private directory containing application.yaml.
docker run --rm --read-only --tmpfs /tmp --cap-drop ALL \
  --security-opt no-new-privileges \
  --mount "type=bind,src=$SLICKFLOW_CONFIG_DIR,dst=/config,readonly" \
  -e SLICKFLOW_DB_URL -e SLICKFLOW_DB_USER -e SLICKFLOW_DB_PASSWORD \
  -e SLICKFLOW_ENGINE_SCHEMA -e SLICKFLOW_GITHUB_WEBHOOK_SECRET \
  -e JAVA_TOOL_OPTIONS=-Xmx512m \
  -p 127.0.0.1:8080:8080 "$SLICKFLOW_RUNTIME_IMAGE" \
  --spring.config.additional-location=file:/config/application.yaml
```

Runtime accepts external Spring YAML; the migration executable reads environment
variables only. Both use the same database URL with dedicated `currentSchema`
and matching engine schema; see [persistence](../architecture/control-plane-persistence.md).
Configure hostname-verified database TLS and its trust material privately. The
container binds HTTP to all container interfaces so host-loopback publication can
reach it; never infer safe public exposure from that setting. Existing Caddy/
tunnel routing and rate limits remain #114. Runtime feature switches retain their
packaged disabled defaults; only enable webhook ingestion/classification for the
initial deployment. See [webhook configuration](github-webhooks.md).

The 512 MiB heap is within the approved provisional 1 GiB runtime budget. It does
not bound total container memory. Verify host cgroup enforcement or approve an
alternative before relying on a container limit. Migration memory is not yet
profiled. Migration failures block runtime startup; no startup DDL, schema repair,
clean, automatic rollback or data deletion is introduced. Follow the deployment
contract's preservation and approval gates before using a persistent database.

## Verified scope

For #110, ARM64 and amd64 image builds passed. On amd64, packaged migration
(including replay), DML-only runtime health, rejected DDL, unrelated-route denial
and JRE-only/non-root image checks passed against disposable PostgreSQL 18.6.
All 90 integration/unit/architecture tests passed on both 17.11 and 18.6; the
18.6 full Maven verify/package run completed successfully. The 17.11 run's final
packaging step encountered a plugin-download failure after all tests passed;
packaging was independently verified by the image builds and 18.6 verify run.
Maven transfer stalls required a temporary local cache and alternate HTTP
transport for test execution; these overrides are not deployment configuration.
ARM64 execution was not verified: this amd64 host lacks ARM emulation and reports
an exec-format error. Repeat the image smoke check natively on ARM64 before
deployment. No Pi/shared-database access, live TLS or load verification is claimed.
