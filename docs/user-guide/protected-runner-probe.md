# Protected deployment runner probe

Tracks [#113](https://github.com/skizzay/slickflow/issues/113) under
[epic #108](https://github.com/skizzay/slickflow/issues/108). This is a standalone
probe entry point on default branch `main`, not epic-to-main integration or a
production deployment workflow. GitHub requires the workflow on the default
branch before offering manual dispatch.

`.github/workflows/deploy_control_plane.yaml` permits manual dispatch in this
repository on `main` or `epic/108`. Its only job requires environment
`control-plane-production` and runner labels `self-hosted`, `linux`, `x64`,
`slickflow-deploy`. Contents/Actions permissions are read-only; OIDC token issuance
is enabled for the approved job. The sole step invokes the administrator-installed
`/usr/local/bin/slickflow-deploy probe`. It performs no checkout, application
migration, deployment or automated approval. Concurrency shares the production
maintenance workflow group and does not cancel an in-progress operation.

Before dispatch, the database admin agent must enroll the exact reviewed workflow
path **`.github/workflows/deploy_control_plane.yaml`**, branch-specific identity
and merged workflow revision into its admission/OIDC policy. The supplied admin
template/tooling originally names a hyphenated path; that is a different identity
and must be reconciled to this underscore filename. Do not weaken policy with a
wildcard to accommodate the mismatch. Enroll the actual merged commit, not the
PR head or an unreviewed future revision. The workflow must also exist at the
reviewed revision on `epic/108` before dispatching that branch.

The admin must confirm the isolated one-job runner, protected environment,
short-lived identity and launcher are ready. The owner then dispatches and
personally approves the protected job in GitHub. A successful probe must be
matched to the controller's sanitized result, maintenance-lock behavior and clean
runner teardown. Submission/queueing alone is not success. Keep tokens, private
inventory and raw controller logs out of public workflow evidence.

This PR verifies workflow syntax and the template boundary only. Live OIDC
admission, protected-job execution and runner teardown remain unverified until
that coordinated probe is performed. Application deployment remains under #113.
