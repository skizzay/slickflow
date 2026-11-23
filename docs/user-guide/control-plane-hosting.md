# Private control-plane hosting

Tracks [#111](https://github.com/skizzay/slickflow/issues/111), under
[epic #108](https://github.com/skizzay/slickflow/issues/108). Depends on #109,
merged through [PR #116](https://github.com/skizzay/slickflow/pull/116).
[Packaging #110](https://github.com/skizzay/slickflow/issues/110) is also integrated
through [PR #117](https://github.com/skizzay/slickflow/pull/117).

The repository supplies dedicated database bootstrap, separate remote-database
runtime and migration Compose recipes, host-specific read-only preflight and
backup/isolated-restore tools. Runtime runs on the ARM64 Pi; the database admin
agent runs the matching migration executable on the amd64 database server.

The administrator's November 15 completion report records LDAP-authenticated
restricted logins, OpenBao secret custody and automated rotation, protected
consumer files, private DNS and hostname-verified TLS, successful positive/negative
connection tests and preserved existing-tenant health. These are administrator
reported results, not application startup evidence. The admin reports initial migration and Pi runtime deployment completed at
artifact `374b4d1bc3a5629f0bfe5065eee12ec64f5e8c5f`, with loopback health UP and
ownership/runtime/default grants verified. GitHub's cancelled job is not a
successful Actions result; the backend completion was reconciled independently.
The initialized source cannot reuse the closed empty-source first-release approval.
SlickFlow backup/restore remains owner-deferred under #123; compatible update,
real-runtime rotation/reconnect and host-reboot acceptance remain pending. An independent Internet port scan was not performed. Private
endpoints, source addresses, secret references and operator commands stay in the
owner-controlled administrator inventory, not this public guide.

Database maintenance requests go through the existing database admin agent.
Public ingress and execution remain disabled. A bounded configuration PR can be reviewed and merged without claiming #111
operational completion. Keep #111 open until its remaining application/recovery
acceptance is verified; the deployment pipeline is #113.

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
roles and the `slickflow` database owned by the migrator. Roles start NOLOGIN
and have no superuser, database-create, role-create, replication or row-security
bypass permissions. It grants runtime CONNECT and restricts PUBLIC database and
public-schema access only within this database. It creates no application schemas
and grants no schema/table privileges. Repetition preserves data and credentials;
unexpected elevated roles, memberships or database ownership stop bootstrap.

The migration service sets `SLICKFLOW_DB_RUNTIME_ROLE=slickflow_runtime`. Flyway
creates missing `slickflow`/`flowable` schemas under the migration identity, applies
V1, and Flowable creates its engine objects. The standalone executable then grants
runtime schema USAGE, table DML and sequence access in one permissions transaction.
It also sets default privileges for future objects created by that same migration
identity. This grant step repeats after every successful migration, including no-op
migration runs; it is deployment setup outside V1, with no runtime startup DDL.
Migration requires the configured runtime role to already exist, be distinct and
unprivileged, and have no inherited roles or schema CREATE access. Existing schemas
must be owned by the migration identity; mismatches fail instead of changing owners.
Grant failure fails the migration executable and blocks runtime startup. Flyway,
Flowable maintenance and the grant transaction are separate steps, not one atomic
migration; serialized maintenance remains mandatory. Existing dedicated schemas
already owned by the migrator need no drop/recreation.

The admin agent provisions the two LDAP service identities and maintains their
credentials in OpenBao. PostgreSQL roles remain separate authorization records;
LDAP validates passwords. Do not assign local PostgreSQL passwords as a fallback.
Automated rotation must update the directory, OpenBao and each consumer file,
coordinate consumer reconnect/recreation, and recover an interrupted generation.
The reported implementation performs these steps with maintenance locking; its
private runbooks own the exact commands, schedules and revocation procedure.

Database ACLs alone cannot prevent these roles using PUBLIC privileges in other
shared databases. Install reviewed, database/role/source-specific HBA rules before
allowing login remotely. Reject these roles on Unix sockets before broad local
trust rules; narrowly allow only the approved TCP sources, including the database
server migration source, before broader rejects/trust rules. The pattern is an exact TLS/LDAP `hostssl` allow for database
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
Select matching immutable native images as described in
[packaging](control-plane-packaging.md). Prepare separate private operator environment configurations on each host:

| Host / recipe | Required local inputs |
|---|---|
| Pi / `deployment/control-plane/compose.yaml` | ARM64 `SLICKFLOW_RUNTIME_IMAGE`, `SLICKFLOW_RUNTIME_PASSWORD_FILE`, TLS URL/CA and approved CPU budget |
| Database server / `deployment/control-plane/compose.migration.yaml` | amd64 `SLICKFLOW_MIGRATION_IMAGE`, `SLICKFLOW_MIGRATION_PASSWORD_FILE`, TLS URL/CA and approved CPU/migration-memory budgets |

Both image labels must identify the same approved full source commit; compare the
two preflight outputs across hosts. The Pi requires no migrator image/password and
the database recipe requires no runtime image/password. Migration uses trusted
host networking to retain the approved database-server source; do not run it from
an unapproved bridge source or mount a Docker socket. A matching standalone JAR
is an admin-operated alternative to the one-shot container.

Materialize only the runtime password file on Pi and only the migration password
file on the database server, outside the checkout,
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
./scripts/check-control-plane-host.sh runtime    # on Pi
./scripts/check-control-plane-host.sh migration  # on database server
```

Preflight is read-only: it never pulls images, changes kernel settings or starts
services. It checks only the selected host role: native non-root image, its own private
secret file, TLS configuration and actual Docker memory-limit support. Runtime
requires ARM64; migration supports native amd64 or ARM64. Read-only verification confirms Pi memory-limit support is now available;
preflight still checks it before use. The 512 MiB heap is not whole-container
containment.

After authorized maintenance, operations use the persistent project identity
`slickflow` with `deployment/control-plane/compose.yaml`, installed by the
operator at `/opt/slickflow/compose.yaml` with private configuration at
`/etc/slickflow/compose.env`. This matches the admin rotation receiver's requested
registration; confirm registration before starting runtime. The receiver requires
an immutable image matching the registered container and refuses unapproved
configuration/image changes. Coordinate registration changes during deployment. Runtime
restart policy is `unless-stopped`; an intentional maintenance stop remains
stopped across Docker restarts. The root filesystem is read-only with bounded
`/tmp`, local logs are rotated, CPU/memory/PID limits are explicit, and HTTP is
published only to host loopback. Webhooks, execution, inbox dispatch, manual
approval and workers are forced off. No public route, database volume or Docker
socket mount is created. Persistent data stays on the existing database host.

Serialize maintenance/deployment through the database admin agent's installed
`maintenance.py` interface. The administrator reports that it acquires database
then Pi locks, holds both through migration/startup, and shares them with rotation.
Use its private runbook for plan staging, exact paths, register/deploy/status/wait
commands and cancel/abort recovery. Submission success is not deployment success;
wait for final operation status and application health. Do not invoke Compose
independently or acquire a separate flock.

Registration freezes reviewed candidates without starting services. Deployment
requires matching immutable native images, exact recipe/config hashes, approved
resource budgets, the expected previous registration and an operator attestation
that ingress is closed. The wrapper does not close ingress itself. It supports
the one-shot migration recipe; standalone JAR execution is not exposed.

The administrator reports successful contention, disconnect, deadline,
cancellation and explicit fence recovery probes. Failure retains durable fences
and affected runtime stays stopped; recovery requires the documented admin abort
and a new approved operation, never schema repair/reset or implicit retry.

Within that coordinated maintenance operation:

1. Verify the exact approved paired revision and per-host preflight results.
2. Stop Pi runtime and keep ingress closed.
3. Have the database admin agent run the matching migration executable on the
   database server using `compose.migration.yaml` (service `migration`), scoped
   migration credentials and hostname-verified TLS through the admin wrapper.
4. On migration/grant failure, preserve data, keep runtime stopped and escalate.
5. Update/confirm the rotation receiver registration and start only the Pi runtime
   with project `slickflow`; verify status-only health and fresh database access.
6. Release maintenance through the admin protocol only after success or its
   documented failure handoff. Rotation must not race these steps.

No command performs automatic schema repair, reset or schema-incompatible rollback.
The administrator reports weekly automated rotation and daily maintenance checks;
future-runtime recreation/health during rotation still needs application evidence.
Failures leave the affected runtime stopped; local failure reporting exists but
external alert delivery is not configured.

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

## Configuration separation checks

```sh
python3 -m unittest discover -s scripts/tests -v
```

These checks render both production recipes independently with synthetic inputs,
assert credential/service separation, migration host networking and loopback-only
runtime publication, and exercise mutable-image preflight rejection. They do not
start services or verify live LDAP/TLS/rotation.

## Disposable verification and evidence

```sh
# Use immutable local image IDs built by #110; these are not production secrets.
export SLICKFLOW_RUNTIME_IMAGE SLICKFLOW_MIGRATION_IMAGE
./scripts/verify-hosting.sh
```

The unique local PostgreSQL 18.6 project uses synthetic data and temporary secrets.
It layers the disposable database overrides over both production recipes rather
than duplicating service definitions. Runtime retains its actual tmpfs, secret
loading, limits and disabled command switches. Migration retains its actual
secret-reading entrypoint and host networking, connecting only to the fixture's
random host-loopback database port. Separate protected runtime/migration password
files use the same disposable fixture value; no production credential is used. Compose v2.24.4 or newer is required for the
fixture's `!override` port replacement. Quoted tmpfs entries preserve comma-separated
mount options as one YAML string; startup is verified by Docker, not only config
rendering.
It exercises schema-free repeated bootstrap, repeated scoped migration with
migrator-owned schemas and runtime grants (including future objects), mounted runtime secret loading,
DML-only startup, role/database restrictions inside the test network, container recreation with
persistent data, custom-format backup and isolated restore with exact fixture-row
comparison, and refusal to overwrite production/nonempty targets. Fixture HBA
uses a private runtime network and loopback-only database publication without
TLS; production verify-full TLS, external network exposure, Pi startup and
real-host reboot are separate required evidence.
Only the unique disposable project's volumes are deleted by its cleanup.

Public PR evidence must contain only source/artifact identities, sanitized
pass/fail outcomes and verification limits. Keep hostnames, addresses, credentials,
user data, SQL dumps and sensitive execution logs in owner-controlled storage.

## Review and operational acceptance

The #111 implementation PR supplies configuration, scoped migration grants,
preflight and disposable recovery verification. Its merge does not close #111 or
assert production acceptance. The admin reports account/TLS/rotation and lock
interface acceptance independently. Deployment after prerequisite integration
still requires approved immutable artifacts, remaining resource budgets,
backup/recovery readiness and a coordinated window. Native application startup,
actual-runtime rotation, application grants, SlickFlow restore and controlled
host-restart evidence must be recorded before completing #111.

The configuration separation tests and PostgreSQL 18.6 Maven suite pass locally.
Disposable packaged migration/replay, DML-only runtime, persistence and isolated
restore checks pass; these do not substitute for live-host acceptance. The fixture
password file is owned by UID/GID 10001 with mode 0400 and is removed with the
unique test fixture; production secrets never enter these tests.

## Failed deployment and corrected release identity

A recipe/source correction requires a new reviewed source revision, immutable
publication and independently approved release policy. Do not rerun a revoked
release or advance a pinned initial-release exception automatically. The admin
must inspect the failed operation and explicitly reconcile/abort retained fences
before admitting a new operation; no migration retry, schema reset or repair is
implicit. Backup work remains owner-deferred under
[backlog #123](https://github.com/skizzay/slickflow/issues/123), not a passed check.
