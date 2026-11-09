# Initial control-plane deployment contract

Tracks [epic #108](https://github.com/skizzay/slickflow/issues/108) and
[target story #109](https://github.com/skizzay/slickflow/issues/109).
This is a proposed operating contract, not evidence of a deployed environment.
Host inventory, access, cost and deployment authorization remain pending owner
confirmation. No host has been inspected or provisioned by this story.

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
| Host | Existing Raspberry Pi | Pending owner confirmation; no access attempted |
| OS and CPU | Supported Linux; build for the measured CPU architecture | Unknown; verify OS version, CPU and 64-bit userspace before choosing images |
| Capacity | One control plane and private PostgreSQL; no workers | RAM, available disk, storage medium and capacity budget unverified |
| Persistence | Dedicated persistent database volume on reliable storage | Device, free-space threshold, restart behavior and backup destination pending |
| Access | Owner-authorized maintenance and deployment identities | Method, permissions and network route pending; never publish credentials |
| Packaging | Docker Compose on one host; no Kubernetes | Proposed; confirm Docker/Compose availability and host support |
| Registry | GHCR with commit-linked immutable digests | Proposed; visibility, access and retention pending |
| HTTPS | Reverse proxy with verified certificate and rate limiting | DNS ownership, inbound route, certificate renewal and proxy choice pending |
| Secrets | Deployment secret store, injected at runtime/maintenance | Store, owner, rotation and recovery access pending |
| Deployment | Manual dispatch of an exact verified commit to an approved GitHub environment | Environment name, approvers, repository-plan support and runner placement pending |
| Cost | No new paid services without separate approval | Hosting, registry, storage/backup and network limits require confirmation |

Before #109 is complete, the owner must approve this record and an authorized
operator must verify the actual host inventory. Record inspection date, sanitized
OS/architecture/RAM/free-storage facts, tool versions and pass/fail access results.
Do not infer target characteristics from the development machine. If access is
unavailable, retain explicit unverified status and keep dependent implementation
blocked. GitHub environment approval availability must be checked; if unavailable,
select an equivalent explicit human gate before implementing deployment.

## Bounded deployment requirements

Only the existing modular Spring Boot/Flowable runtime and PostgreSQL are in
scope. Enable signed webhook ingestion and asynchronous classification; expose
status-only health. Explicitly keep `slickflow.execution.enabled`,
`slickflow.execution.inbox.enabled`, `slickflow.manual-approval.enabled` and
`slickflow.worker.enabled` false. No worker, execution container, GitHub write,
OAuth provider or autonomous merge is required. See the
[inbox architecture](../architecture/webhook-inbox.md) for implemented behavior.

Publish matching runtime and migration executables from the same tested commit,
with artifact digests and pipeline-run provenance. Verify with real PostgreSQL
before publication; select the target image platform only after inventory.
Deploy only the approved source commit/artifacts, never a floating tag. Limit
initial operation to one runtime and one database; approve numeric CPU, memory,
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
