# Roadmap

The active roadmap consists of three **proposed Epics awaiting owner review**.
No child stories are planned or authorized until that review. Epic creation,
backlog cleanup and this document do not approve implementation, deployment,
execution activation or merge.

| Order | Epic | Intended outcome |
|---|---|---|
| 1 | [#128 — Live control plane, no registered workflows](https://github.com/skizzay/slickflow/issues/128) | A healthy deployed service supports an empty workflow registry and does not seed definitions on startup/restart. |
| 2 | [#129 — Register/unregister project-defined workflows](https://github.com/skizzay/slickflow/issues/129) | Authorized workflow lifecycle operations with project ownership, validation, version identity and preserved history; registration starts no execution. |
| 3 | [#130 — Trigger execution and advance the next step](https://github.com/skizzay/slickflow/issues/130) | Start or resume the correct registered workflow/run safely, using a trigger model to be discussed with the owner before story breakdown. |

## Goal 1 — Live control plane with no registered workflows

Reuse the deployed Spring Boot/PostgreSQL foundation and accepted live webhook
receipt/classification evidence. A webhook can be stored and classified without
registering a workflow or starting work. Keep execution disabled.

A healthy service with execution disabled is not proof that the workflow registry
is empty: the current [persistence bootstrap](../architecture/control-plane-persistence.md)
registers a packaged definition. Verify both application registration and engine
definition inventory, and support normal startup/restart with zero registered
workflows. Preserve retained data and history; this planning reset authorizes no
live deletion, schema reset, workflow removal or configuration change.

## Goal 2 — Workflow registration and unregistration

Each project owns its workflow definition and toolchain steps. Different C++, Java,
Python and mixed-language projects can use different sequences without requiring a
new control-plane implementation per project. Reusable activities/templates may
be shared. SlickFlow Developer is project-independent.

Agree the definition/source contract, registration interface, authorized actors,
validation/version semantics and the effect of unregistration on referenced
versions/history/runs during Epic review. Unregistration does not imply destructive
engine-history deletion. Registering or unregistering a workflow does not execute
it; unregistering the last one leaves a healthy service.

## Goal 3 — Start and advance execution

Discuss the trigger model with the owner before defining stories: manual commands,
APIs, events or webhooks are choices, not settled requirements. Decide start versus
resume behavior, workflow/version/run/activity correlation, verified activity
completion, approvals, initial executor and failure/retry/cancellation semantics.
Flowable remains the architecture's sequencing boundary; workers execute assigned
activities. An issue or agent assertion cannot manufacture approval or verified
operational completion.

The longer-term direction includes distinct SlickFlow Developer and Skizzay SRE
identities serving multiple projects, with project-owned workflows and durable
request/result coordination that removes manual developer/admin document handoffs.
This is retained direction, not a requirement to build a complete autonomous
issue-to-PR/SRE platform in the first execution slice. Project configuration cannot
grant credentials or bypass approval, execution isolation or human merge authority.

## Review and delivery policy

Review the three Epic outcomes, exclusions, decisions and ordering first. Create
stories only after the owner has reviewed the corresponding Epic and agreed its
scope. Historical stories are reference material, not an approved delivery plan or
automatically satisfied dependencies. Reuse verified existing implementation;
check actual integration before relying on it. Preserve small reviewable changes,
meaningful tests, necessary documentation and human merge gates.

## Deferred concerns and evidence limits

Broader worker/Codex execution, branch/PR publication, planning/DAG scheduling,
review/remediation, feedback/skill learning, release automation, cloud adapters and
branding work are outside the immediate Epic-only roadmap unless explicitly
reprioritized. Backup remains owner-deferred and is not a restored MVP blocker.
Portable operating roles/break-glass design, host-reboot, rotation and recovery
acceptance remain future concerns, without unperformed checks being marked passed.

The owner accepts the live receipt/classification service as the receipt MVP.
This does not establish an empty registry, full issue-to-PR automation, every
previous operational acceptance criterion or final epic-to-main integration.

The [2026-11-26 consolidation record](../research/roadmap-reset-2026-11-26.md)
preserves the retired issue map and earlier roadmap. Closed superseded issues are
not completed-feature evidence. Existing architecture/contract documents describe
implemented capabilities or longer-term proposed design, not extra active Epics.
