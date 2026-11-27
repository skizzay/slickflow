# Roadmap consolidation — 2026-11-26

The owner requested an Epic-only reset with three sequential outcomes and no
stories before Epic review. The active [roadmap](../requirements/roadmap.md) is
#128 (empty-registry live control plane), #129 (registration lifecycle), then #130
(execution/next-step triggers, model to be discussed).

## Disposition and preservation

Initially reviewed 62 open issues and closed them as `not_planned` / superseded, not as
completed implementations. Each retains its original body and a transition note
linking its consolidation home. The homes below retain relevant design/evidence
for later evaluation; they do not import every historical requirement into the new
Epic. No stories were created. Existing code, PR branches, live resources and
approval history were preserved; no operational changes were made.

Five stale planning PRs (#19, #20, #25, #30, #72) were closed without merging or
deleting their branches. Their original descriptions remain available. Delivered
mainline/epic code is unaffected. Future backup (#123) and portable operating roles
(#122) are retained as deferred concerns in #128; historical naming work is
withdrawn from current scheduling, without any naming-clearance claim.

| Retired issue | Historical subject | Consolidation home(s) |
|---|---|---|
| [#1](https://github.com/skizzay/slickflow/issues/1) | [Epic] Foundation: control plane and GitHub integration | [#128](https://github.com/skizzay/slickflow/issues/128), [#129](https://github.com/skizzay/slickflow/issues/129), [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#2](https://github.com/skizzay/slickflow/issues/2) | [Epic] Planning: structured epics, approvals and dependency DAG | [#129](https://github.com/skizzay/slickflow/issues/129) |
| [#3](https://github.com/skizzay/slickflow/issues/3) | [Epic] Execution: Java workers, pluggable providers and branch lifecycle | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#4](https://github.com/skizzay/slickflow/issues/4) | [Epic] Review: Copilot feedback and bounded remediation | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#5](https://github.com/skizzay/slickflow/issues/5) | [Epic] Integration: epic validation and human-approved release | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#6](https://github.com/skizzay/slickflow/issues/6) | [Epic] Operations: reliability, budgets and cloud portability | [#128](https://github.com/skizzay/slickflow/issues/128), [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#9](https://github.com/skizzay/slickflow/issues/9) | [Tracking] Worker protocol, authentication and lease operations | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#10](https://github.com/skizzay/slickflow/issues/10) | [Tracking] Java worker and isolated execution | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#11](https://github.com/skizzay/slickflow/issues/11) | [Tracking] Approved issue-to-PR vertical slice | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#12](https://github.com/skizzay/slickflow/issues/12) | [Tracking] Structured plan validation and approval | [#129](https://github.com/skizzay/slickflow/issues/129) |
| [#13](https://github.com/skizzay/slickflow/issues/13) | [Tracking] Codex environment and scoped-access validation | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#15](https://github.com/skizzay/slickflow/issues/15) | [Tracking] Bounded workflow and GitHub recovery | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#16](https://github.com/skizzay/slickflow/issues/16) | [Spike] Verify Copilot review webhook behavior | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#17](https://github.com/skizzay/slickflow/issues/17) | [Tracking] Story integration eligibility | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#27](https://github.com/skizzay/slickflow/issues/27) | Document Java-first Flowable control-plane architecture | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#28](https://github.com/skizzay/slickflow/issues/28) | Document pluggable logical-agent and SCM identity architecture | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#29](https://github.com/skizzay/slickflow/issues/29) | Require verified GitHub issue links when agents create pull requests | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#35](https://github.com/skizzay/slickflow/issues/35) | [Tracking] Provisional SlickFlow rename | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#36](https://github.com/skizzay/slickflow/issues/36) | [Planning] Reduce backlog to small, reviewable delivery slices | [#128](https://github.com/skizzay/slickflow/issues/128), [#129](https://github.com/skizzay/slickflow/issues/129), [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#39](https://github.com/skizzay/slickflow/issues/39) | [Story] Atomically claim one eligible job | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#40](https://github.com/skizzay/slickflow/issues/40) | [Story] Renew the current attempt lease | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#41](https://github.com/skizzay/slickflow/issues/41) | [Story] Accept a fenced, idempotent worker outcome | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#42](https://github.com/skizzay/slickflow/issues/42) | [Story] Poll and report a fake activity from the Java worker | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#43](https://github.com/skizzay/slickflow/issues/43) | [Story] Launch and clean up one isolated Docker job | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#44](https://github.com/skizzay/slickflow/issues/44) | [Story] Run a Codex activity through the Java worker | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#45](https://github.com/skizzay/slickflow/issues/45) | [Story] Stop and clean up a cancelled or timed-out job | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#47](https://github.com/skizzay/slickflow/issues/47) | [Story] Create one pinned job from an approved inbox event | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#48](https://github.com/skizzay/slickflow/issues/48) | [Story] Publish one story branch from the approved epic head | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#49](https://github.com/skizzay/slickflow/issues/49) | [Story] Publish one tested story pull request | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#50](https://github.com/skizzay/slickflow/issues/50) | [Story] Demonstrate the approved issue-to-PR vertical slice | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#51](https://github.com/skizzay/slickflow/issues/51) | [Spike] Validate repository-scoped GitHub App access | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#52](https://github.com/skizzay/slickflow/issues/52) | [Spike] Verify Codex sign-in lifecycle and failure handling | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#53](https://github.com/skizzay/slickflow/issues/53) | [Story] Pin a minimal Codex and Java execution image | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#54](https://github.com/skizzay/slickflow/issues/54) | [Story] Read normalized GitHub branch, PR and check observations | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#55](https://github.com/skizzay/slickflow/issues/55) | [Story] Recover a lost PR publication acknowledgement | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#56](https://github.com/skizzay/slickflow/issues/56) | [Story] Reconcile an expired lease before permitting retry | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#57](https://github.com/skizzay/slickflow/issues/57) | [Story] Parse one versioned epic/story plan format | [#129](https://github.com/skizzay/slickflow/issues/129) |
| [#58](https://github.com/skizzay/slickflow/issues/58) | [Story] Validate missing dependencies and cycles | [#129](https://github.com/skizzay/slickflow/issues/129) |
| [#59](https://github.com/skizzay/slickflow/issues/59) | [Story] Resolve pinned plan definitions and mandatory policy | [#129](https://github.com/skizzay/slickflow/issues/129) |
| [#60](https://github.com/skizzay/slickflow/issues/60) | [Story] Approve a validated plan revision explicitly | [#129](https://github.com/skizzay/slickflow/issues/129) |
| [#61](https://github.com/skizzay/slickflow/issues/61) | [Story] Reject a PR targeting the wrong epic branch | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#62](https://github.com/skizzay/slickflow/issues/62) | [Story] Invalidate stale story checks when the epic head moves | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#63](https://github.com/skizzay/slickflow/issues/63) | [Docs] Inventory the provisional SlickFlow rename | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#64](https://github.com/skizzay/slickflow/issues/64) | [Story] Rename Java packages and Maven coordinates | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#65](https://github.com/skizzay/slickflow/issues/65) | [Story] Rename runtime configuration and Docker assets | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#66](https://github.com/skizzay/slickflow/issues/66) | [Task] Rename the GitHub repository and update current links | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#67](https://github.com/skizzay/slickflow/issues/67) | [Research] Record provisional-name clearance follow-up | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#68](https://github.com/skizzay/slickflow/issues/68) | [Story] Authorize one operator job cancellation command | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#69](https://github.com/skizzay/slickflow/issues/69) | [Story] Obtain short-lived GitHub App access for one repository | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#70](https://github.com/skizzay/slickflow/issues/70) | [Story] Advance one waiting workflow activity after an accepted result | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#71](https://github.com/skizzay/slickflow/issues/71) | [Story] Publish one tested commit to the prepared story branch | [#130](https://github.com/skizzay/slickflow/issues/130) |
| [#93](https://github.com/skizzay/slickflow/issues/93) | [Epic] Define and plan repository-specific workflow configuration | [#129](https://github.com/skizzay/slickflow/issues/129) |
| [#108](https://github.com/skizzay/slickflow/issues/108) | [Epic] Deploy the control plane through CI/CD and prove live GitHub webhook persistence | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#109](https://github.com/skizzay/slickflow/issues/109) | [Story] Confirm the initial control-plane deployment target and operating contract | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#110](https://github.com/skizzay/slickflow/issues/110) | [Story] Package matching control-plane runtime and migration artifacts | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#111](https://github.com/skizzay/slickflow/issues/111) | [Story] Provision private PostgreSQL and persistent control-plane hosting | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#112](https://github.com/skizzay/slickflow/issues/112) | [Story] Verify and publish immutable control-plane artifacts in CI | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#114](https://github.com/skizzay/slickflow/issues/114) | [Story] Expose authenticated GitHub webhook ingress over HTTPS | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#115](https://github.com/skizzay/slickflow/issues/115) | [Story] Prove live GitHub webhook persistence, deduplication and restart recovery | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#122](https://github.com/skizzay/slickflow/issues/122) | [Backlog] Define portable deployment roles, approval and break-glass boundaries | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#123](https://github.com/skizzay/slickflow/issues/123) | [Backlog] Establish SlickFlow backup policy and verified recovery automation | [#128](https://github.com/skizzay/slickflow/issues/128) |
| [#127](https://github.com/skizzay/slickflow/issues/127) | Automate development-to-SRE handoff across projects with separate GitHub App identities | [#129](https://github.com/skizzay/slickflow/issues/129), [#130](https://github.com/skizzay/slickflow/issues/130) |

## Integration correction — 2026-11-27

Closing #108 during planning cleanup was premature: its delivered branch remains
37 commits ahead of main. #108 is reopened for residual final integration through
[PR #132](https://github.com/skizzay/slickflow/pull/132), with explicit human
approval. The current disposition is 61 retired legacy issues, one retained
integration tracker (#108), and three proposed new Epics. The table preserves the
original consolidation homes, not proof that all old issues remain closed.
Integrate the existing baseline first, then reconcile roadmap PR #131 with it;
do not lose packaging, CI, hosting or ingress implementation. No new stories,
automatic merge or live mutation follows from this correction.

## Earlier roadmap (historical)

The following is the superseded roadmap text for historical context, not current
priority, verified delivery state or implementation authority.

# Roadmap

Target throughput: 4–6 epics/week across multiple repositories, 6–8 stories/epic. These are capacity targets, not demonstrated throughput.

## Milestone 1 — Vertical slice
Approved test story -> webhook -> durable job -> local Docker Codex worker -> story branch -> tests -> pull request. Single repository and one active job. No autonomous merging.

## Milestone 2 — Epic planning
Structured issue templates; acceptance-criteria coverage; dependency DAG with cycle detection; explicit human plan approval; epic branch creation.

## Milestone 3 — Dependency-aware execution
Global/repo/epic concurrency controls; branch freshness checks; leases, heartbeats, retries and worker recovery; downstream dispatch only after prerequisite merge.

## Milestone 4 — Review loop
Ordered QA → specialist reviewer-agent reviews → human review; webhook-triggered developer remediation restarting at QA; separate durable feedback capture; two-attempt default limit and escalation. Feedback-driven skill improvement requires evaluated, human-approved changes; concrete delivery slices remain to be scheduled.

## Milestone 5 — Integration and release
Epic acceptance verification, architecture review, final epic PR to main, human merge approval and release preparation.

## Milestone 6 — Operations and portability
Pause/resume/cancel, telemetry, AI and compute cost reporting, security hardening, cloud worker compatibility testing.

## First sprint tasks
1. Spring Boot skeleton and database migrations.
2. GitHub App webhook receiver with signature verification and durable inbox.
3. Job and worker API contract.
4. Java polling worker with lease and heartbeat.
5. Disposable Docker Codex execution image and safe credential handling.
6. Test story -> branch -> PR end-to-end demonstration.

Each task must specify dependencies, acceptance criteria, verification, and completion evidence.

## Feasibility checkpoint — 2026-10-22

[Issue #18](https://github.com/skizzay/slickflow/issues/18) is closed with an
accepted bounded research result; see the [synthesis](../research/issue-18-results.md).
PR #21 is retained as an unmerged experiment archive, not a production dependency.
Bootstrap, webhook inbox, lifecycle guards and worker OAuth2 authentication are
implemented. The current delivery sequence is manual plan approval (#46), pinned
event-to-job creation (#47), then atomic worker claiming (#39). Approval alone
does not dispatch work; prerequisite PRs must still integrate into the Execution
epic before being treated as satisfied. #13 still owns scoped GitHub credential and provider operational
validation; #11 owns the actual approved-issue-to-PR demonstration; #15 owns real
GitHub reconciliation. Milestone 1 is not complete. No new generic Flowable POC
is required; use the existing evidence while implementing and testing those stories.
Research acceptance does not waive human epic approval or implementation merge gates.
