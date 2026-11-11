# Consumer user guide

Instructions for people setting up and using SlickFlow belong here.

Planned topics: installation, connecting a repository, approving work, following execution and reviewing results. Further setup instructions will be added as those capabilities become available.

- [Local control-plane bootstrap](local-control-plane.md) — migrate the database, run the local health endpoint and optionally enable approved execution and configured signed-event dispatch; includes project identity and preservation of existing local resources.

- [GitHub webhook inbox](github-webhooks.md) — enable signed delivery ingestion and inspect processing status.

- [OAuth2 worker authentication](worker-authentication.md) — Spring Boot OAuth2 settings and principal mapping; job endpoints remain unimplemented.

- [Manual plan approval](manual-plan-approval.md) — configure one epic/story pair, issue approval/invalidation commands and understand internal parent preparation.

- [Deployment planning prerequisites](../requirements/control-plane-deployment.md) — dated two-host inventory, provisional runtime RAM budget and unresolved enforcement and remaining decisions/host verification before deployment; not an executable deployment runbook.

- [Control-plane packaging](control-plane-packaging.md) — matching non-root Java 21 runtime/migration images, immutable source identity and disposable PostgreSQL 18.6 smoke verification (#110).

- [Private control-plane hosting](control-plane-hosting.md) — dedicated shared-database roles, migrator-owned schemas/runtime grants, external secrets, bounded Pi hosting and isolated recovery (#111); actual host verification pending.
