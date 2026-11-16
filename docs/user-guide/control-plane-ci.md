# Control-plane verification and publication

Tracks [#112](https://github.com/skizzay/slickflow/issues/112) under
[epic #108](https://github.com/skizzay/slickflow/issues/108). Packaging #110 is
integrated through PR #117; split-host configuration #111 through PR #118.
[Packaging](control-plane-packaging.md) owns image contents and local builds;
[hosting](control-plane-hosting.md) owns deployment inputs and maintenance.

## Source and permission boundary

`.github/workflows/control-plane.yaml` validates PRs targeting `main` or
`epic/108` and pushes to those branches. Each native amd64/ARM64 validation job
runs configuration/publication guard tests, the full Maven/PostgreSQL 18.6 suite,
paired image builds, packaged smoke checks and disposable hosting/recovery checks.
GitHub-hosted `ubuntu-24.04` and `ubuntu-24.04-arm` runners are used; no homelab
runner, deployment credential or database access is required. Native ARM64 runner
checks verify architecture execution, not Pi-specific capacity or networking.

PR validation has only `contents: read`, checkout credential persistence is off,
and no registry login occurs. The workflow does not use `pull_request_target`,
privileged PR approval paths or an artifact from untrusted code for publication.
Third-party actions are pinned to full commit SHAs; update pins explicitly.

Publication runs only in `skizzay/slickflow`, for a push or manual dispatch on
`main` or `epic/108`, after **both** validation jobs succeed. It rebuilds on each
native architecture and smoke-tests the actual pair before registry login. Only
these separate trusted jobs have `packages: write`; they use the short-lived
`GITHUB_TOKEN`, never production or personal credentials. No GitHub write or
package token is supplied to validation jobs. No deployment occurs here.
Branch merge permissions remain the source authorization boundary; restrict
trusted branches to reviewed human-approved integration.

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

Manual dispatch can start validation on other selected refs, but publication
is restricted to the two trusted branches. GitHub requires the workflow on the
default branch before offering dispatch. Until then, merging
this workflow into `epic/108` triggers its first trusted publication. Never push
an unreviewed change directly to a trusted branch to exercise publication.

## Verification and completion

Local tests exercise trusted/untrusted source rejection, simulated push failure
without a success record, and digest/provenance creation. Actionlint checks the
workflow. Actual PR checks and first trusted publication must be observed in
GitHub; local simulations alone do not complete #112. A bounded implementation
PR may merge to enable the first trusted run; leave #112 open until the published
pair and gate behavior are verified. Deployment pipeline #113 and native Pi
startup/real database initialization remain separate acceptance work.
