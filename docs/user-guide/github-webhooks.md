# Configure the local GitHub webhook inbox

Tracks [#8](https://github.com/skizzay/slickflow/issues/8). First follow the
[local control-plane guide](local-control-plane.md) to build and migrate. The initial
V1 schema includes the webhook inbox and event classification tables.

Webhooks are disabled by default. To enable them, supply these environment
variables to the runtime container from your environment or secret manager:

- `SLICKFLOW_GITHUB_WEBHOOK_ENABLED=true`
- `SLICKFLOW_GITHUB_WEBHOOK_SECRET`: the secret configured for the GitHub App webhook.

This is a signing secret, not the GitHub App private-key PEM. Do not put it in
tracked files, URLs, process arguments or logs. Compose does not forward these
host variables implicitly: pass `-e SLICKFLOW_GITHUB_WEBHOOK_ENABLED` and
`-e SLICKFLOW_GITHUB_WEBHOOK_SECRET` to its `run` command, without literal values.
For example, after exporting the variables securely in your shell:

```sh
docker compose -p slickflow-dev run --rm --service-ports \
  -e SLICKFLOW_GITHUB_WEBHOOK_ENABLED -e SLICKFLOW_GITHUB_WEBHOOK_SECRET \
  build java -jar control-plane/target/control-plane-0.1.0-SNAPSHOT.jar --server.address=0.0.0.0
```

The webhook URL is `/webhooks/github`. Configure GitHub to send JSON and the
matching secret. Local Compose still publishes only host loopback; configuring
an external HTTPS route and a live GitHub App is separate deployment/integration
work. The implementation does not read the PEM, provision a tunnel or contact GitHub.

A valid delivery returns 202 after persistence; a matching retry returns 200.
Same UUID with changed content returns 409. A 503 is not an acknowledgement:
retry the original delivery after database recovery. Unsupported event types are
classified as UNSUPPORTED; no event starts an agent or approves a plan.

Optional YAML settings under `slickflow.github.webhook`:

| Setting | Default | Purpose |
|---|---|---|
| `max-bytes` | `1048576` | Maximum raw request size; up to 10 MiB supported |
| `processing-enabled` | `true` | Poll/classify persisted inbox deliveries |
| `poll-interval` | `PT1S` | Delay between bounded processing batches |

For inspection, `webhook_inbox` stores only sanitized pointers and a body hash;
`webhook_event` stores the processing classification. Raw payloads are deliberately
unavailable. Pending verified records resume after restart. See the
[inbox design](../architecture/webhook-inbox.md) for limits and recovery semantics.

Run the entire PostgreSQL regression suite with `./scripts/verify-bootstrap.sh`.
The tests use synthetic events and temporary secrets and never send a GitHub webhook.

## Hosted receipt-only configuration (#114)

[Issue #114](https://github.com/skizzay/slickflow/issues/114) depends on #113,
integrated through [PR #125](https://github.com/skizzay/slickflow/pull/125).
The optional `deployment/control-plane/compose.webhook.yaml` overlay enables
receipt and asynchronous classification on the existing loopback runtime. It
replaces the base command explicitly; an environment variable alone cannot
override the base command's disabled-webhook setting. Execution, inbox dispatch,
manual approval and workers remain disabled. No schema change is required.

The admin delivers a distinct OpenBao-managed signing secret as an absolute
`SLICKFLOW_WEBHOOK_SECRET_FILE` path outside the checkout, private and readable
by the container: UID 10001 with mode 0400, or UID 0/10001 and GID 10001
with mode 0440. Preflight requires regular files and rejects symlinks, unrelated
group access and write/execute/special bits for both database and signing secrets.
Compose mounts it at
`/run/secrets/SLICKFLOW_GITHUB_WEBHOOK_SECRET` for the existing Spring configtree.
The database password stays a separate secret. No App PEM, LDAP password or
runner credential is used for webhook signing.

Read-only host checks, after secure environment provisioning:

```sh
./scripts/check-control-plane-host.sh runtime-webhook
# Inspect configuration only; this does not start or replace the service.
docker compose -f deployment/control-plane/compose.yaml \
  -f deployment/control-plane/compose.webhook.yaml config --quiet
```

The overlay is application configuration, not permission to change the host.
The admin must first review a preserving configuration transition for the
initialized database, register its exact immutable release/configuration and
serialize it with maintenance and rotation. Do not rerun the closed initial
empty-source deployment approval or reset the database. Use the approved admin
interface to replace/restart runtime; keep ingress closed until local HMAC and
classification checks pass. A new release must pass compatibility checks against
the existing V1 schema and registered workflow before deployment.

The selected public hostname is `webhooks.slickflow.ai`. DNS, trusted HTTPS,
origin restrictions and an effective rate limiter remain admin work, unverified
by this overlay. Before exposure, allow only POST `/webhooks/github`, deny other
public paths (including health), preserve raw body bytes and signature/delivery/
event headers, enforce the 1 MiB limit and verify rate-limit responses. Keep
PostgreSQL private and suppress payload/signature logging. Health remains
available locally. No paid service is authorized by this configuration.

To disable receipt, the admin closes the public route first and uses the approved
preserving transition back to the base recipe, whose command disables webhooks.
Keep stored inbox/classification data. Rotation requires coordinated OpenBao and
GitHub webhook-secret replacement, runtime recreation to reread the mounted
secret, and positive/new-key plus negative/old-key verification before reopening.
Only one signing key is supported: quiesce deliveries and use GitHub redelivery
to recover the interruption; do not claim overlap or zero-loss live rotation.

`./scripts/verify-hosting.sh --webhooks` exercises the production overlay against
an isolated PostgreSQL fixture and matching local image pair. It checks synthetic
signed ping/issues, retry/conflict, rejected signatures and encoding, durable
classification and zero jobs/runs/dispatch records. Native CI runs both disabled
and receipt-only fixture modes. These checks do not verify public TLS, rate
limits or actual GitHub delivery; those remain #114/#115 acceptance evidence.
Backup remains owner-deferred under [#123](https://github.com/skizzay/slickflow/issues/123).
