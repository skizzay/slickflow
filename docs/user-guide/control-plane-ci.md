# Control-plane verification and publication

Native CI builds on [#112](https://github.com/skizzay/slickflow/issues/112),
with main-only publication under [#135](https://github.com/skizzay/slickflow/issues/135).
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
Each native publication job rebuilds and smoke-tests its actual pair before
registry login. Only these jobs have `packages: write`. They use the short-lived
`GITHUB_TOKEN`, never production or personal credentials. No GitHub write or
package token is supplied to validation jobs. No deployment occurs here.
Reviewed integration and main protection remain separate requirements for
production release eligibility. See the [release contract](../requirements/branching-and-versioning.md#goal-1-release-contract-133).

## Artifacts and provenance

Each trusted run publishes these two repositories for both architectures:

- `ghcr.io/skizzay/slickflow-runtime`
- `ghcr.io/skizzay/slickflow-migration`

Discovery tags are `FULL_COMMIT-amd64` and `FULL_COMMIT-arm64`. Tags can move on
rerun: only `repository@sha256:DIGEST` references are deployment identities.
Images carry the full source revision and non-root UID/GID 10001. Pi runtime and
database-host migrator use different native image digests with the same revision.
There is no multi-platform manifest/index requirement for these split hosts.

The run summary and `control-plane-provenance-ARCH-ATTEMPT` workflow artifact contain
`provenance-ARCH.json`: source revision, architecture, runtime/migration registry
digests, pipeline URL and attempt. Each rerun uses a separate artifact name so it cannot
collide with or overwrite an earlier attempt. Workflow artifacts are retained for 30 days;
preserve the approved deployment identities privately beyond that if needed.
This is a traceability record, not a signed supply-chain attestation. No raw
application payloads, private network inventory or production logs are uploaded.

A failed test prevents publication jobs from starting. A publication failure can
leave an individual image pushed; it never emits a successful pair record before
both pushes/digest checks pass. Do not deploy from a failed/incomplete workflow
or combine architectures from different source revisions. Require full-run success
and both provenance records before selecting deployment artifacts. There is no
automatic image purge or rollback.

## Registry access and reruns

GHCR package creation/access must be available to the repository workflow token.
Initial package visibility can be private; public source does not imply anonymous
package pulls. Confirm visibility and pull access before staging images. Any
private registry pull credential belongs in the approved OpenBao process, never
in the checkout or deployment plan. Do not change package visibility implicitly.
No new paid runner or service is configured.

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

## Verification and completion

Local tests exercise the workflow eligibility check, independent publication
guard, SHA mismatch, partial push failure and digest/provenance creation.
Actionlint checks the workflow. Observe both native checks on the story PR and
verify that publication jobs are skipped. Observe first main publication and
its provenance separately during release verification under Epic #128.

Receipt-only ingress configuration (#114) is also checked with
`./scripts/verify-hosting.sh --webhooks` on each native architecture before
publication, in addition to the disabled-webhook fixture. This exercises the
production overlay and synthetic HMAC receipt/classification with no dispatch;
it does not establish public TLS/rate limiting or live GitHub acceptance. See the
[webhook hosting contract](github-webhooks.md#hosted-receipt-only-configuration-114).
