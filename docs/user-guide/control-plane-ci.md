# Control-plane verification and publication

Native CI builds on [#112](https://github.com/skizzay/slickflow/issues/112),
with main-only publication under [#135](https://github.com/skizzay/slickflow/issues/135)
and the private Forgejo registry cutover under [#148](https://github.com/skizzay/slickflow/issues/148).
[Packaging](control-plane-packaging.md) owns image contents and local builds;
[hosting](control-plane-hosting.md) owns deployment inputs and maintenance.

## Source and permission boundary

`.github/workflows/control-plane.yaml` validates PRs targeting `main` or any
`epic/*` branch, including `epic/128`. It also validates main pushes and manual
dispatches. Each native amd64/ARM64 validation job
runs configuration/publication guard tests, the full Maven/PostgreSQL 18.6 suite,
paired image builds, packaged smoke checks and disposable hosting/recovery checks.
GitHub-hosted `ubuntu-24.04` and `ubuntu-24.04-arm` runners are used; no homelab
runner, deployment credential or database access is required. Native ARM64 runner
checks verify architecture execution, not Pi-specific capacity or networking.

The workflow is named `Control-plane artifacts`. Its exact native job check
names are `Verify (amd64)` and `Verify (arm64)`. These are the check identities
for [main branch protection](main-branch-protection.md), pinned to the GitHub
Actions app (`15368`).

PR validation has only `contents: read`, checkout credential persistence is off,
and no registry login occurs. The workflow does not use `pull_request_target`,
privileged PR approval paths or an artifact from untrusted code for publication.
Third-party actions are pinned to full commit SHAs; update pins explicitly.

Publication requires a push or manual dispatch in `skizzay/slickflow` on the exact
`refs/heads/main` ref and successful results from **both** native validation jobs.
A permissionless job makes case-sensitive comparisons of the event context before
the publication job can start. The publication script independently verifies
that context and the checked-out SHA before registry login and before any push.
Each native publication job targets the `control-plane-publication`
environment and rebuilds and smoke-tests its actual pair before accessing the
registry handoff. The workflow uses GitHub read permissions. PR validation has
no publication environment, Forgejo credential or private access path.
Reviewed integration and main protection remain separate requirements for
production release eligibility. See the [release contract](../requirements/branching-and-versioning.md#goal-1-release-contract-133).

## Artifacts and provenance

Each trusted run publishes `slickflow-runtime` and `slickflow-migration` in the
same approved Forgejo namespace for both architectures once the administrator
enables credential delivery.

Discovery tags are `FULL_COMMIT-amd64` and `FULL_COMMIT-arm64`. Tags can move on
rerun: only `repository@sha256:DIGEST` references are deployment identities.
Images carry the full source revision and non-root UID/GID 10001. Pi runtime and
database-host migrator use different native image digests with the same revision.
There is no multi-platform manifest/index requirement for these split hosts.

The run summary and `control-plane-provenance-ARCH-ATTEMPT` workflow artifact
contain `provenance-ARCH.json` with the source revision, architecture, run URL,
attempt, approved registry binding hash and two role-specific manifest digests.
Keep the host and namespace in private configuration. GitHub retains distinct
archives per attempt for 30 days. Preserve the verified evidence independently
of that retention. The archives provide traceability and carry no signed
supply-chain attestation.

A failed test prevents publication jobs from starting. A publication failure can
leave an individual image pushed; it never emits a successful pair record before
both pushes/digest checks pass. Do not deploy from a failed/incomplete workflow
or combine architectures from different source revisions. Require full-run success
and both provenance records before selecting deployment artifacts. There is no
automatic image purge or rollback.

## Registry access and reruns

The administrator owns the approved network path, TLS, scoped Forgejo publisher
and read-only consumer identities, OpenBao custody and credential rotation.
Confirm private namespace visibility, capacity and retention before enabling
publication. Restrict the publication environment to reviewed main and require
owner approval without bypass. The OpenBao delivery and protected environment
configuration are pending operational verification. Without an approved handoff,
the publication step fails closed.

The private binding is the exact lowercase DNS host and namespace, separated by
one slash. `registry_binding_sha256` is the SHA-256 of its UTF-8 bytes without
a trailing newline, with the `sha256:` prefix. The administrator records the
approved digest as `SLICKFLOW_REGISTRY_BINDING_SHA256` in protected publication
configuration. After the native build and smoke checks, the approved delivery
adapter must create a regular file with mode 0600 owned by the publication
process user at the absolute `SLICKFLOW_REGISTRY_AUTH_FILE` path. The JSON
contains `registry`, `registry_binding_sha256`, `username` and `token`.
Publication checks both hashes against the protected configuration before
contacting Forgejo. Docker reads the token through standard input and uses a
temporary client configuration. The publisher removes that temporary configuration
on success or failure, and the workflow removes the handoff in its always-run
cleanup step.

New publication targets only the approved Forgejo binding. Preserve historical
GHCR images, evidence and rollback access, including already deployed images.
Deletion, copying and retention changes require separate authorization. New
release selection requires Forgejo evidence on reviewed main.

Use the Actions run page to inspect checks and download both provenance records.
To repeat a known run without selecting an arbitrary source:

```sh
gh run rerun RUN_ID --repo skizzay/slickflow
gh run watch RUN_ID --repo skizzay/slickflow --exit-status
```

Manual dispatch can start validation on other selected refs. Only dispatch on
`refs/heads/main` is eligible for publication. GitHub requires the workflow on
the default branch before offering dispatch. Prior Epic-built artifacts remain
ineligible even if their commit later enters main.

## Verify a release candidate

[Story #136](https://github.com/skizzay/slickflow/issues/136) provides a read-only
[release candidate verifier](../../scripts/verify_release_candidate.py).
Run it from a trusted, reviewed checkout with Python 3, the GitHub CLI
authenticated to github.com with repository administration and Actions read
access, and Docker Buildx with the administrator-approved read-only session for
both private Forgejo packages. Supply the private binding through operator
configuration independent of the candidate.

| Input | Value |
|---|---|
| `--run-id` | GitHub Actions run ID for an exact-main push or manual dispatch after integration |
| `--source-revision` | Full lowercase Git SHA of the owner-merged source commit |
| `--configuration-revision` | Full lowercase Git SHA of the intended deployment configuration recorded by the owner |
| `--integration-receipt` | Owner-retained version 2 JSON receipt for the exact merge, checks, configuration and registry binding |
| `SLICKFLOW_REGISTRY` environment variable | Approved private host and namespace binding from operator configuration |
| `--trusted-receipt-digest` | SHA-256 pin in `sha256:` form independently obtained from the owner |

The verifier reconciles the [owner receipt](main-branch-protection.md#release-integration-receipt)
with GitHub's repository, merged PR, merge parents, main history, native PR checks
and live protection. It requires a same-repository PR integrated by the owner
using a two-parent merge commit. Squash and rebase integrations are outside this
path. The source checkout must match the verifier's reviewed workflow,
publication code, registry binding implementation and protection policy. The
workflow and guard confirm the exact branch ref during publication. GitHub's
run API returns the short branch name.

Both native verify jobs and both native publish jobs must have succeeded in the
run's current attempt, along with the publication source job. The verifier
downloads the two provenance archives from GitHub by artifact ID, checks their
API digests and upload times, and compares their run, attempt, revision and
platform. It checks the private binding against the pinned owner receipt and
both provenance archives before resolving all four manifest digests in
[the registry](control-plane-packaging.md#release-candidate-images). The
archives supply only digests. The verifier constructs the exact references
from its own approved binding. It checks the current main and PR workflow
attempts again before emitting the record. Rerunning only failed jobs may keep
prior-attempt jobs and artifacts.
Rerun all jobs for one complete main attempt and verify again. A rerun of the
PR check workflow requires owner reconciliation of the pinned integration
evidence.

Success writes a version 2 JSON record with the binding hash and manifest
digests for release and [deployment approval](control-plane-hosting.md#release-candidate-evidence). An
unknown, expired, missing or inconsistent result exits with a nonzero status and
a diagnostic on standard error. Check provider read access and availability when
a read fails, or reconcile mismatches with the owner before retrying. Preserve
the receipt and selection evidence independently of GitHub's artifact retention.
The verifier makes no release or deployment changes. Positive live verification
requires an eligible main run following reviewed integration into main.

## Verification and completion

Local tests exercise main-only eligibility, exact checkout, private credential
routing, partial pushes, digest-only provenance, rejected registry evidence and
redacted output. Run Actionlint and observe both native story PR checks with
publication skipped. Cutover requires an authorized disposable Forgejo
push, digest inspection and pull through the approved path, plus separate
runtime and migration consumer pull evidence. The first eligible main
publication and its provenance are tracked in
[#139](https://github.com/skizzay/slickflow/issues/139).

Receipt-only ingress configuration (#114) is also checked with
`./scripts/verify-hosting.sh --webhooks` on each native architecture before
publication, in addition to the disabled-webhook fixture. This exercises the
production overlay and synthetic HMAC receipt/classification with no dispatch;
it does not establish public TLS/rate limiting or live GitHub acceptance. See the
[webhook hosting contract](github-webhooks.md#hosted-receipt-only-configuration-114).
