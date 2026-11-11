# Private control-plane hosting

Tracks [#111](https://github.com/skizzay/slickflow/issues/111), under
[epic #108](https://github.com/skizzay/slickflow/issues/108). Depends on #109,
merged through [PR #116](https://github.com/skizzay/slickflow/pull/116).
[Packaging #110](https://github.com/skizzay/slickflow/issues/110) is also integrated
through [PR #117](https://github.com/skizzay/slickflow/pull/117).

The repository supplies repeatable database bootstrap, a remote-database hosting
Compose file, read-only host preflight and database backup/isolated-restore tools.
Local disposable verification is implemented. Read-only Pi inspection verified
SSH administration, Debian 13/ARM64, Docker startup enabled at boot, Compose,
Python and flock. The dedicated database, schemas and two scoped NOLOGIN roles have now been
created on the shared PostgreSQL 18.6 service using the tested bootstrap. Owner
and role privilege flags were verified; passwords, application migrations and
network authorization are not configured. Pi runtime provisioning, private
network/TLS authorization, ARM64 runtime verification and a controlled host
reboot remain unverified. The kernel command line explicitly disables the memory controller
(`cgroup_disable=memory`), and Docker reports memory/swap limit support false.
Database DNS resolution and SSH administration now succeed from the workstation;
the Pi also resolves the database service. The earlier DNS failure is resolved.
No boot configuration, running service or existing tenant data was changed. These instructions do not authorize
another application's interruption, secret-store changes or reinitialization.
The [deployment contract](../requirements/control-plane-deployment.md) owns
remaining access, cost, resource and deployment decisions. Keep PRs draft until
required target evidence exists; the application deployment pipeline is #113.

## Database bootstrap and identities

Use PostgreSQL 18 client tools and an owner-authorized cluster administrator via
a private libpq service file. Keep connection details, service/pass files and
secrets outside the checkout. The admin service selects a maintenance database.
Do not run any disposable verification script against the shared service.

```sh
# Run from the repository root on the authorized administration host.
PGSERVICE=slickflow_admin psql -X -v ON_ERROR_STOP=1 \
  -f deployment/control-plane/bootstrap.sql
```

Bootstrap creates only dedicated `slickflow_migrator` and `slickflow_runtime`
roles and the `slickflow` database with `slickflow`/`flowable` schemas. Roles start
NOLOGIN and have no superuser, database-create, role-create, replication or
row-security-bypass permissions. Migrator owns only the dedicated database and
schemas; runtime has CONNECT, schema USAGE and table DML/sequence access, including
default privileges for future migrator-owned objects. Public database privileges
and public-schema access are revoked only within SlickFlow's database. Existing
objects are validated: elevated roles, memberships or foreign ownership stop the
script. Repetition does not reset data, rotate credentials or silently repair
privilege drift. Bootstrap advisory locks serialize its own critical sections.

A trusted operator assigns separate generated login secrets through the approved
secret process, for example interactive psql `\password` followed by enabling
LOGIN for each role. Never put literal passwords in SQL, arguments, logs or Git.
OpenBao exists, but its SlickFlow policy, machine authentication, access route,
secret ownership and rotation/recovery procedures still need selection and
verification. No new secret-store administrator credentials are created here.

Database ACLs alone cannot prevent these roles using PUBLIC privileges in other
shared databases. Install reviewed, database/role/source-specific HBA rules before
allowing login remotely. The pattern is an exact `hostssl` allow for database
`slickflow` plus each role's approved source CIDR, followed by IPv4/IPv6 catch-all
rejects for both SlickFlow roles. Place them before broader matching rules; retain
other tenants' existing rules. Never broaden an existing application's allow to
SlickFlow. Validate configuration and reload HBA through the established operator
procedure without restarting or replacing the shared database.

Verify private listener/publication, host firewall and ingress/NAT behavior using
authorized probes. Verify hostname/certificate validation and successful DML-only
runtime startup from the Pi, rejected domain/cluster DDL, and rejection from
unapproved sources/to unrelated databases. No new database port is published by
the application Compose file. Local tests do not establish public unreachability.

## Runtime host and secrets

Use the Pi Docker/Compose installation with Docker startup enabled at boot.
Select matching immutable ARM64 images as described in
[packaging](control-plane-packaging.md). Prepare private operator environment
configuration containing these references and approved CPU/migration-memory
budgets. Image labels must identify the same full source commit.

Materialize separate runtime and migration password files outside the checkout,
readable by container UID/GID 10001 and inaccessible to other users. Compose
file-backed secrets preserve source-file ownership/permissions; declaring a mode
in Compose does not fix a host file. The runtime imports the password through
Spring configtree; the migrator wrapper reads its own secret into the process
environment without logging or passing its value in argv. No development password
or secret-store token is supplied in the repository.

Provide the database CA as a read-only file and an external JDBC URL selecting
`currentSchema=slickflow`, `sslmode=verify-full` and
`sslrootcert=/run/trust/postgresql-ca.crt`. Do not embed credentials in the URL.
The engine schema is fixed to `flowable` in this hosting recipe. Required external
variables are declared in the Compose file and checked by:

```sh
./scripts/check-control-plane-host.sh
```

Preflight is read-only: it never pulls images, changes kernel settings or starts
services. It requires ARM64/non-root paired images, appropriate private secret
files, TLS configuration and actual Docker memory-limit support. The known Pi
memory-cgroup issue blocks this check until fixed or an alternative is explicitly
approved and implemented; the 512 MiB heap is not whole-container containment.

After authorized maintenance, operations use the persistent project identity
`slickflow-control-plane` with `deployment/control-plane/compose.yaml`. Runtime
restart policy is `unless-stopped`; an intentional maintenance stop remains
stopped across Docker restarts. The root filesystem is read-only with bounded
`/tmp`, local logs are rotated, CPU/memory/PID limits are explicit, and HTTP is
published only to host loopback. Webhooks, execution, inbox dispatch, manual
approval and workers are forced off. No public route, database volume or Docker
socket mount is created. Persistent data stays on the existing database host.

Serialize maintenance/deployment across operators and automation. Stop runtime
before running the maintenance-profile migration service; only start it after
successful migration, then verify status-only health. Use distinct credentials
for those two steps. Pipeline serialization and automated deployment are #113;
Compose alone supplies no distributed maintenance lock. Use the same private lock
path on the Pi for every authorized operator; direct database administration must
coordinate with that maintenance window too. For example, after all preflight and
authorization gates pass:

```sh
(
  set -e
  flock -n 9
  compose=(docker compose -p slickflow-control-plane \
    -f deployment/control-plane/compose.yaml)
  "${compose[@]}" stop runtime
  "${compose[@]}" --profile maintenance run --rm migration
  "${compose[@]}" up -d runtime
  # Check after startup; a failed probe is not a successful deployment.
  curl --max-time 5 --fail http://127.0.0.1:8080/actuator/health
) 9>"${SLICKFLOW_MAINTENANCE_LOCK:?shared private lock path required}"
```

This local lock is not coordination across independent hosts. No command here performs
automatic schema repair, database reset or cross-schema-version rollback.

For acceptance, record a synthetic sanitized database marker, restart/recreate the
application and verify it, then arrange owner-approved maintenance windows for
real Pi and database-host restart tests and verify persistence/health again.
Coordinate with all shared-service owners; container recreation is not a host
reboot. Do not delete volumes or retained evidence to simulate recovery.

## Backup and isolated restore

Use client tools matching PostgreSQL 18 and private libpq service/pass files.
Select a trusted migration/backup identity with access to all SlickFlow objects.
The custom-format dump retains ownership/ACL records, but not cluster roles,
passwords, HBA, CA or secret-store state. Preserve those separately through their
own approved recovery process. Treat backups as sensitive executable SQL/data:
restrict access, encrypt storage/transport and restore only trusted backups.

```sh
# Select an existing private directory OUTSIDE this checkout.
PGSERVICE=slickflow_backup SLICKFLOW_BACKUP_DIR="$PRIVATE_BACKUP_ROOT" \
  ./scripts/backup-control-plane.sh

# Operator first creates a NEW slickflow_restore_* database owned by the migrator,
# isolated from production traffic, with separately reviewed access rules.
# The service selects that new target; choose the specific backup directory.
PGSERVICE=slickflow_restore SLICKFLOW_BACKUP_DIR="$PRIVATE_BACKUP_DIRECTORY" \
  ./scripts/restore-control-plane.sh
```

Backup checks the selected database name, writes into a unique private directory,
validates archive readability and records a SHA-256 checksum. It never overwrites
a previous backup or changes database state. It is a consistent single-database
snapshot; secrets/configuration are not covered by that snapshot.

Restore refuses the production database name and nonempty targets, verifies the
checksum and restores in one transaction without `--clean`, database creation or
automatic deletion. It checks migration/registry readability; acceptance additionally
requires expected row/constraint checks and a compatible runtime health test. Keep
the restore isolated until verified, and remove it only by a separate approved
operator action. A checksum establishes file integrity, not backup authenticity.

Before deployment, approve backup destination/owner, encryption, frequency,
retention, off-site policy and recovery-time/data-loss budgets; no recurring timer
or automatic purge is installed. A database volume alone is not backup coverage.
An incompatible pre-release V1 revision blocks startup: preserve required data
and obtain a human-approved preservation/reinitialization decision. Do not restore
older application/schema artifacts over live new writes or promise rollback
across incompatible V1 revisions.

## Disposable verification and evidence

```sh
# Use immutable local image IDs built by #110; these are not production secrets.
export SLICKFLOW_RUNTIME_IMAGE SLICKFLOW_MIGRATION_IMAGE
./scripts/verify-hosting.sh
```

The unique local PostgreSQL 18.6 project uses synthetic data and temporary secrets.
It exercises repeated bootstrap, scoped migration, mounted runtime secret loading,
DML-only startup, role/database restrictions inside the test network, container recreation with
persistent data, custom-format backup and isolated restore with exact fixture-row
comparison, and refusal to overwrite production/nonempty targets. Fixture HBA
uses a private Docker network without TLS; production verify-full TLS, external
network exposure, Pi startup and real-host reboot are separate required evidence.
Only the unique disposable project's volumes are deleted by its cleanup.

Public PR evidence must contain only source/artifact identities, sanitized
pass/fail outcomes and verification limits. Keep hostnames, addresses, credentials,
user data, SQL dumps and sensitive execution logs in owner-controlled storage.
