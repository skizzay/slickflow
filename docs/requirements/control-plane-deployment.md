# Initial control-plane deployment contract

Tracks [epic #108](https://github.com/skizzay/slickflow/issues/108) and
[target story #109](https://github.com/skizzay/slickflow/issues/109).
This is a proposed operating contract, not evidence of a deployed environment.
The owner has selected the existing Pi, PostgreSQL service and Caddy, and
approved a provisional runtime memory budget; enforcement is not yet available. Remaining inventory, access, cost
and deployment authorization decisions are pending. The existing shared database
upgrade and dated host inspection are operational evidence; SlickFlow hosting
and its database identities have not been provisioned.

## Baseline and integration

The initial source baseline is main commit
`0b364db6ea0aa0a13804186fd306e1d9f488ba18`. Its ancestry includes bootstrap
[PR #22](https://github.com/skizzay/slickflow/pull/22), merge `7fa6fa2`, and
verified inbox [PR #23](https://github.com/skizzay/slickflow/pull/23), merge `0e51840`.
Both merge commits were verified as ancestors of `epic/108` using Git.

`epic/108` starts at that baseline. Child branches use `feature/108-STORY`,
created from the latest epic head, and their PRs target `epic/108`.
The first branch is `feature/108-109`. No child dependency is satisfied until its
PR merges into this epic. Final integration into main requires human approval.
The request to start #108 authorizes this planning work; it does not approve
unknown target/access/cost decisions or authorize a live deployment.

## Target decision record

Record only sanitized facts here. Keep hostnames, private addresses, account
identifiers, access instructions and credentials in an owner-controlled private
inventory/secret store. Public evidence may say that access was verified without
publishing its sensitive details.

| Decision | Proposal | Approval / verification |
|---|---|---|
| Runtime host | Existing Raspberry Pi, Debian 13 / ARM64 | Authorized November 9 inspection reconfirmed OS/architecture and existing Forgejo; Pi model undocumented; SlickFlow runtime/userspace checks pending |
| Database host | Shared PostgreSQL 18.6 on separate Ubuntu Server 26.10 / x86-64 host | Owner-approved upgrade completed November 9; existing Authentik/Forgejo verified; SlickFlow database, schemas and DDL/DML roles not provisioned |
| Capacity | Provisional runtime budget of 1 GiB including a 512 MiB heap (`-Xmx512m`); no workers | Owner approved budget; November 7 inspection found Docker/kernel memory-limit enforcement unavailable and Docker stats zero; November 9 available-RAM/storage snapshots exist, but SlickFlow peak usage and containment remain unverified |
| Persistence | Dedicated SlickFlow database on the selected remote PostgreSQL service | SlickFlow storage, access restrictions and backup coverage unverified |
| Access | Existing local SSH administration; dedicated deployment/maintenance identities pending | Dated owner inventory verifies administration only; existing application-specific database TLS/HBA permissions do not authorize SlickFlow |
| Packaging | Docker Compose runtime on Pi; reuse remote database | Pi Docker/Compose deployments previously verified; fresh versions and runtime support checks pending |
| Registry | GHCR with commit-linked immutable digests | Proposed; visibility, access and retention pending |
| Ingress | Existing Cloudflare Tunnel public ingress; proposed route through Pi Caddy to runtime | Pi Caddy currently serves legacy loopback compatibility routes; SlickFlow public route, origin security, TLS ownership and rate limiting unprovisioned/unverified |
| DNS | Dedicated local SlickFlow service record resolves to Pi | Owner inventory only; this does not establish public DNS or ingress |
| Secrets | Existing OpenBao 2.7.2 available on database host | Initialized/operational with admin login and isolated recovery verified November 2; SlickFlow selection/integration, policies and machine credentials pending |
| Deployment | Manual dispatch of an exact verified commit to an approved GitHub environment | Environment name, approvers, repository-plan support and runner placement pending |
| Cost | No new paid services without separate approval | Hosting, registry, storage/backup and network limits require confirmation |

Inventory sources: the [owner review on PR #116](https://github.com/skizzay/slickflow/pull/116#issuecomment-6754501694)
and subsequent owner-authorized operational inspection, PostgreSQL upgrade and
acceptance on November 9, 2026 (November 10 UTC). OpenBao verification dates to
November 2. Private hostnames, addresses, access details and recovery material
remain in the owner-controlled inventory; this record contains sanitized facts.
The infrastructure maintenance approval does not authorize SlickFlow provisioning
or deployment.

The deployment spans two hosts. The Pi's retained PostgreSQL 17 instance is for
retired-service data/rollback and is not the selected SlickFlow database. Shared
PostgreSQL memory/storage belong to the remote host, outside the Pi allocation.
Existing tenants must remain isolated; provision SlickFlow-specific database,
schemas, DDL/DML roles and source/HBA restrictions. Existing Forgejo TLS access
and successful database/files backup/isolated restore do not verify SlickFlow
connectivity or backup coverage. Recurring/off-site backup policy is outstanding.
The development/test default remains PostgreSQL 17.11. Under #110, all 90
SlickFlow tests and full Maven verify/package passed against disposable PostgreSQL
18.6 on amd64, plus packaged migration/replay and DML-only runtime health. This
verifies local compatibility, not production TLS/HBA authorization or ARM64
execution. Native ARM64 image smoke checks remain required before deployment.
Do not silently change test pins or the shared database version.

The owner reports roughly 3 GB freed on the Pi by retiring an existing service;
November 9 inspection found about 7.1 GiB available RAM and 98 GiB free storage
on the Pi, plus about 28 GiB available RAM and 77 GiB free storage on the database
host. These are dated availability snapshots; repeat them before deployment and
measure SlickFlow under representative load. The approved 1 GiB budget includes
heap and native overhead. It is not an enforceable container limit today: verify
memory-cgroup support or obtain approval for an alternative before relying on
containment. `-Xmx512m` caps only heap. Caddy, the tunnel and OS have separate Pi
memory needs. Migration memory remains to be measured and budgeted for serialized
maintenance. Validate startup and representative webhook traffic before claiming
a measured requirement; zero Docker stats is not evidence of zero memory usage.

### Verified infrastructure upgrade and remaining operational work

The shared PostgreSQL service was upgraded from 16.15 to **18.6** using a new
volume after coordinated backups and quiescing existing application writes.
Exact restored table contents, application role password hashes, ownership and
ACLs matched the source. Existing database credentials, LDAP identities, tokens
and application secrets were preserved. Private publication, source/database/role
HBA restrictions and hostname-verified TLS remain in place; the certificate sync
was updated for PostgreSQL 18's versioned data directory and its timer is active.

Live acceptance covered Authentik core/worker/LDAP health, directory search, real
Pi Forgejo connections over verify-full TLS 1.3, existing package tokens,
package reads/publication/cleanup, and unchanged denial of unrelated Pi-to-database
SSH/HTTPS. The owner accepted browser sign-ins. Existing public package ingress
was reopened and verified through HTTPS with an existing scoped token.
A fresh coordinated PostgreSQL 18/files backup restored into isolated PostgreSQL,
Authentik and Forgejo copies; exact data, pg_amcheck, readiness, existing login/token
and package hashes passed. This evidence covers existing services only.

The original PostgreSQL 16 volume and final migration backups remain retained.
New writes make rollback a deliberate preservation/reconciliation decision.
Recurring/off-site backup scheduling and retention, a controlled real-host reboot
test, and eventual retirement of retained PostgreSQL 16 data remain separate
follow-ups. No deletion or host reboot was performed. These completed operations
do not provision SlickFlow, satisfy its backup/restore or connectivity gates, or
approve its deployment. The Pi memory-containment issue remains unresolved.

### SlickFlow-specific remaining gates

Reuse specifically the Pi Caddy, not the separate database-host Caddy used for
private Authentik/OpenBao HTTPS. Proposed ingress is Cloudflare Tunnel → Pi Caddy
→ runtime. Verify/select the exact public route and origin access/transport,
certificate ownership/renewal and rate-limit enforcement before exposure. Existing
Pi Caddy does not establish public TLS ownership. No second proxy is planned.
Pi access to OpenBao must be established independently of database access;
SlickFlow policies, machine authentication, rotation and recovery are unprovisioned.

Before actual provisioning/deployment, the owner must approve remaining operating
decisions and an authorized operator must recheck the target inventory. Record inspection date, sanitized
OS/architecture/RAM/free-storage facts, tool versions and pass/fail access results.
Do not infer target characteristics from the development machine. If access is
unavailable, retain explicit unverified status and keep dependent implementation
blocked. GitHub environment approval availability must be checked; if unavailable,
select an equivalent explicit human gate before implementing deployment.

## Bounded deployment requirements

Only the existing modular Spring Boot/Flowable runtime and a dedicated database
on the selected remote PostgreSQL 18.6 service are in scope. Reuse Pi Caddy
behind the existing Cloudflare Tunnel as the proposed ingress path;
a second proxy is not planned. Rate-limit enforcement must be verified before
public exposure. Enable signed webhook ingestion and asynchronous classification; expose
status-only health. Explicitly keep `slickflow.execution.enabled`,
`slickflow.execution.inbox.enabled`, `slickflow.manual-approval.enabled` and
`slickflow.worker.enabled` false. No worker, execution container, GitHub write,
OAuth provider or autonomous merge is required. See the
[inbox architecture](../architecture/webhook-inbox.md) for implemented behavior.

Publish matching runtime and migration executables from the same tested commit,
with artifact digests and pipeline-run provenance. Verify with real PostgreSQL
before publication; select the target image platform only after inventory.
Deploy only the approved source commit/artifacts, never a floating tag. Limit
initial operation to one runtime on the Pi and one dedicated remote database. The provisional
runtime memory budget above is approved; approve remaining CPU, migration-memory,
disk, backup retention and ingress-rate budgets before provisioning. Exceeding a
budget or requiring a paid resource holds deployment for an owner decision.

PostgreSQL stays on a private network without a public port. Permit only HTTPS
POST `/webhooks/github` and the deliberately selected status-only health route;
deny other routes at ingress. Preserve signed raw bytes and required headers,
reject invalid certificates, bound request size and rate, and avoid body/header
logging. Receipt-only validation needs a webhook signing secret, not a GitHub App
private key or write token. Keep the Docker socket out of untrusted containers.

## Maintenance, failure and preservation

Serialize the entire deployment/maintenance operation per environment, including
manual operations. Quiesce ingress and stop runtime before schema maintenance.
Use a DDL migration identity for the separate `-migrate.jar`, followed by a
separate DML-only runtime identity. Inject secrets without tracked files, literal
command arguments or sensitive logs. Both executables use the same database URL
with dedicated `currentSchema` and matching engine schema; see
[persistence ownership](../architecture/control-plane-persistence.md).

Preserve data before maintenance and verify a bounded backup/restore drill in an
isolated database before relying on recovery. Restart tests must prove persistence
across application and host restart. Define backup ownership, frequency, retention,
restore-time/data-loss limits and a private storage destination before deployment.
A volume alone is not a backup. Do not treat the development Compose administrator
or disposable test volumes as deployment configuration.

There is one pre-release V1 schema, with no revision-to-revision upgrade path.
Checksum/schema incompatibility blocks deployment. Never clean, repair or recreate
the database automatically. Preserve required data and obtain explicit human
approval for any reinitialization. Application rollback is permitted only after
verifying schema and registered-workflow compatibility; it is not promised across
incompatible V1 revisions.

A migration, startup or health failure fails the pipeline and leaves ingress
closed. Report sanitized status and retain artifact identity for diagnosis; never
publish successful deployment status after failed verification. Keep incompatible
runtime stopped, preserve the database, and require an operator recovery decision.
Later ingress verification must check HMAC rejection, committed 202 receipts,
idempotent 200 redelivery and asynchronous classification with sanitized UUID/SQL
evidence; no raw payloads or sensitive logs belong in public evidence.

## Delivery and completion gates

#109 has no child-story dependencies. After its approved contract merges:
#110 packages artifacts, while #111 provisions persistence/hosting; #112 follows
#110, #113 follows #111 and #112, #114 adds HTTPS ingress, and #115 records live
receipt/restart evidence. None is completed by this planning document.

Verification for #109 is review of the approved decision record against actual
host inspection and baseline ancestry. Documentation/link checks verify the
written contract only; they do not establish host readiness. Operational runbooks
for deploy, inspection, redelivery, restart, backup/restore, ingress shutdown,
rotation and recovery must accompany their implementing stories. This milestone
proves receipt/classification, not Milestone 1 issue-to-PR automation.

## Implemented packaging boundary

[#110](https://github.com/skizzay/slickflow/issues/110) supplies matching JRE-only
runtime/migration images from one archived source revision, pinned base digests,
non-root identities and a disposable PostgreSQL 18.6 image smoke check. See
[build/run and verification instructions](../user-guide/control-plane-packaging.md).
Packaging does not publish artifacts, provision services or authorize deployment.

## Hosting configuration boundary

[#111](https://github.com/skizzay/slickflow/issues/111) supplies repeatable dedicated
database/role bootstrap, remote-database Compose hosting, a read-only preflight
and private backup/isolated-restore tools. See the
[hosting guide](../user-guide/control-plane-hosting.md). Actual target provisioning,
network/TLS authorization, secret-store integration, memory enforcement and
controlled host-reboot evidence remain pending; local tests do not satisfy those
operational acceptance gates. No public ingress is added.
