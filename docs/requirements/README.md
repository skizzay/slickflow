# Requirements

Describe what SlickFlow should do, its constraints and acceptance criteria here. GitHub issues track individual implementation work.

- [Roadmap](roadmap.md) — three goal Epics: main-release workflow-free control plane (#128, story breakdown authorized), registration lifecycle (#129), then execution/next-step triggers (#130); owner review precedes stories for each Epic.
- [Staged review and feedback](review-and-feedback.md) — proposed QA, specialist-agent and human gates, a separate feedback store and governed skill improvement (#100).
- [Main-only GitFlow and semantic versions](branching-and-versioning.md) — owner-directed default main/epic/story bases and explicit overrides (#133); broader release/versioning and hotfix design remains proposed (#100).
- [Roadmap consolidation record](../research/roadmap-reset-2026-11-26.md) — historical issue map; earlier Foundation/Planning/Execution and other trackers are superseded, not additional active Epics.

- [Single-worker protocol v1](worker-protocol.md) — proposed message and lease contract (#37), with implemented Boot-configured OAuth2 authentication boundary (#38).

- [Manual plan approval contract](../architecture/manual-plan-approval.md) — implemented single-pair approval/invalidation boundary (#46), without dispatch.

- [Initial control-plane deployment](control-plane-deployment.md) — proposed target inventory, operating decisions and delivery gates (#108/#109); dated Pi/remote-service inventory, completed shared PostgreSQL 18.6 upgrade and provisional RAM budget recorded; memory enforcement verified; admin-reported LDAP/OpenBao and private TLS access complete; live deployment and receipt/classification reported by the admin and accepted by the owner; remaining recovery/operational evidence is distinguished from completed integration.

- [Deployable control-plane packaging](../user-guide/control-plane-packaging.md) — #110 artifact identity, ARM64 build and runtime/migration verification contract.

- [Control-plane hosting operations](../user-guide/control-plane-hosting.md) — #111 database/role bootstrap, migrator-owned schemas and runtime grants, recovery and required target evidence.

- [Control-plane CI and publication](../user-guide/control-plane-ci.md) — native PostgreSQL/image verification, trusted-source GHCR publication and digest/run traceability (#112).
