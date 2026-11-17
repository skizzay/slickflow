# Protected control-plane maintenance

Tracks [#113](https://github.com/skizzay/slickflow/issues/113) under
[epic #108](https://github.com/skizzay/slickflow/issues/108). This standalone
workflow entry point on default branch `main` is separate from epic-to-main
application integration. GitHub requires the workflow on the default branch
before offering manual dispatch.

## Workflow and fixed launcher

`.github/workflows/deploy-control-plane.yaml` accepts manual dispatch in this
repository on `main` or `epic/108`. Its job requires environment
`control-plane-production` and runner labels `self-hosted`, `linux`, `x64`,
`slickflow-deploy`. Contents/Actions permissions are read-only; OIDC token issuance
is enabled for the approved job. There is no checkout, secret retrieval or
approval automation. Dispatch expressions enter environment variables, never
shell source. The fixed commands are:

```text
/usr/local/bin/slickflow-deploy probe
/usr/local/bin/slickflow-deploy deploy --release RELEASE_ID
```

`action` defaults to `probe`, which rejects a release input. `deploy` requires
exactly 32 lowercase hexadecimal characters. The release ID selects an independently
approved private controller policy; it cannot supply commands, paths, recipes,
credentials, resource overrides or mutable image tags. Invalid input exits before
the launcher is invoked. Concurrency shares the production maintenance group
and does not cancel an in-progress operation.

The administrator confirms a 40-minute deployment client budget, 45-minute
workflow timeout and 50-minute isolated VM/admission lifespan including boot and
cleanup. The backend has a 35-minute hard limit with bounded cleanup; probe keeps
its shorter client deadline. Queueing/running is not success: only verified
`complete` returns zero. Usage, busy, authorization/readiness denial, failure and
timeout have distinct nonzero launcher exits. A timeout or lost response requires
trusted status inspection, not blind resubmission or an implicit rollback.

## Enrollment and release approval

The database admin agent must enroll the exact reviewed path
**`.github/workflows/deploy-control-plane.yaml`**, branch-specific identity and
actual merged workflow revision into its admission/OIDC policy. This matches the
admin tooling. Do not weaken revision matching with a wildcard or substitute a
PR head. A new workflow revision requires explicit reviewed reenrollment. The
current successful probe pin does not authorize the extended deployment workflow.
Enroll each branch separately; do not use a main revision to authorize epic/108.

Before enabling deploy, the owner/admin must approve a complete private release
policy binding native immutable images, artifact source revision, verified
publication run/attempt, recipe/config hashes, expected previous registration,
resource limits, expiry/revocation and current readiness evidence. Artifact
revision and deployment-workflow revision are distinct. Private policies, secrets,
backup files, controller paths and raw logs remain outside this public repository.

The selected service envelope is 1 CPU and 1 GiB each, with runtime heap 512 MiB.
Backup retention/custody, RPO/RTO and evidence freshness require explicit owner
policy; an assumed homelab policy or successful synthetic restore is insufficient.
Admin must capture and verify compliant current recovery evidence and closed
ingress before readiness. Initial webhook/execution/inbox/manual-approval/worker
switches remain disabled. Missing, stale, expired, revoked or inconsistent release
and readiness evidence must block deployment.

The owner performs any secret-prompting enrollment in their private terminal;
no administrator credential belongs in chat or agent tools. Only after reviewed
workflow enrollment and release/readiness verification may the owner/application
agent dispatch. The owner personally approves the protected job; the trusted admin
then admits a fresh runner for that exact run, attempt and release. No agent may
approve or bypass that GitHub gate.

## Execution and acceptance boundary

The broker uses the existing database-then-Pi locks through staging, stop,
source/TLS verification, one-shot migration/grants, registration promotion,
runtime recreation and health. It shares the locks with rotation. Accepted
operations remain database-supervised across runner loss. Failure leaves affected
runtime stopped and fences retained; trusted cancellation/reconciliation and
explicit recovery are required. Jobs cannot abort fences, reset schemas, roll
back data or change approvals. Ingress remains closed.

The protected probe succeeded in
[attempt 5](https://github.com/skizzay/slickflow/actions/runs/43960261892/attempts/5)
at the earlier enrolled revision `5ec4aeb122f5d14c1a737bbcae14148279adefd1`.
Its sanitized completion, no-private-IP/JWT-like public-log scan and runner
registration cleanup were independently checked. Admin reports backend/VM cleanup;
negative identity cases include unit coverage rather than every live wrong-claim
combination. This is probe acceptance, not application deployment.

The admin reports the deploy extension installed and tested with unit/disposable
fixtures, with live deploy disabled pending approvals. This workflow change is
verified by Actionlint and local input-routing tests:

```sh
python3 -m unittest discover -s scripts/tests -p test_deployment_workflow.py -v
```

No live deploy has run. Actual migration, native Pi runtime startup, health,
permissions, compatible recovery and production persistence acceptance remain
required under #113/#111. Record only sanitized release/revision/digests,
publication/deployment run identities, operation/final phase and acceptance results;
never upload raw controller/migration logs. A successful job submission alone is
not a successful deployment.
