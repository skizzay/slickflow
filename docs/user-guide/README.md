# Consumer user guide

Instructions for people setting up and using SlickFlow belong here.

Planned topics: installation, connecting a repository, approving work, following execution and reviewing results. Further setup instructions will be added as those capabilities become available.

- [Local control-plane bootstrap](local-control-plane.md) — migrate the database, run the local health endpoint and optionally enable approved execution and configured signed-event dispatch; includes project identity and preservation of existing local resources.

- [GitHub webhook inbox](github-webhooks.md) — enable signed delivery ingestion and inspect processing status; includes the optional receipt-only hosting overlay, secret delivery and pending admin ingress gates (#114).

- [OAuth2 worker authentication](worker-authentication.md) — Spring Boot OAuth2 settings and principal mapping; job endpoints remain unimplemented.

- [Manual plan approval](manual-plan-approval.md) — configure one epic/story pair, issue approval/invalidation commands and understand internal parent preparation.

- [Deployment planning prerequisites](../requirements/control-plane-deployment.md) — dated two-host inventory, selected runtime budget, verified containment and remaining ingress/operating decisions; not an executable deployment runbook.

- [Control-plane packaging](control-plane-packaging.md) — matching non-root Java 21 runtime/migration images, immutable source identity and disposable PostgreSQL 18.6 smoke verification (#110).

- [Private control-plane hosting](control-plane-hosting.md) — dedicated shared-database roles, migrator-owned schemas/runtime grants, read-only secret-file ownership checks, LDAP/OpenBao credentials, separate Pi runtime/database-server migration hosting and production-recipe isolated recovery checks (#111); admin-reported runtime startup/grants verified; further update/recovery acceptance pending.

- [Control-plane CI and publication](control-plane-ci.md) — native verification for main and Epic PRs, stable job check names, and main-only GHCR publication with digest/run provenance (#112, #135) Read-only verification binds reviewed main integration, current native publication and immutable image pairs (#136).
- [SlickFlow main branch protection](main-branch-protection.md) — required PRs and native checks, human merge approval, policy readback, and emergency restoration (#142).
- [Protected control-plane maintenance](protected-runner-probe.md) — protected probe/approved-release dispatch, pre-Bash startup-hook removal, exact identity enrollment, readiness and recovery gates (#113); backend deployment reported complete, Actions cancellation and remaining acceptance distinguished.
