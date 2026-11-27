# Main-only GitFlow and semantic versions

The default branch policy below follows the owner's instructions under
[Epic #128](https://github.com/skizzay/slickflow/issues/128), delivery rules
[#133](https://github.com/skizzay/slickflow/issues/133). The versioning/release and
hotfix design retained from [#100](https://github.com/skizzay/slickflow/issues/100)
remains proposed where not separately approved. The
[BPMN/Mermaid reference](../architecture/workflow-reference.md) depicts that broader
proposed process, including optional release/hotfix branches; it does not override
the default branch flow or implement runtime branch/release handlers.

## Branches and release identities

`main` is the only permanent integration branch. There is no `develop` branch.
Supporting branches are temporary and use exact approved commit bases:

| Branch | Created from | PR target / purpose |
|---|---|---|
| `epic/ISSUE` | Approved, current `main` commit | Coordinate approved child stories and acceptance checks |
| `feature/EPIC-STORY` | Fresh approved epic head | Merge into that epic after verified review/tests and human merge approval |
| `release/X.Y.Z` | Only under explicit instructions for a release-staging edge case | Alternative staging path, never an automatic step in the default Epic flow |
| `hotfix/X.Y.Z` | Only under explicit instructions, from an approved released `main` commit | Proposed urgent-fix exception; scope/base/target need explicit approval |

Default delivery is main → epic → story → epic → main. Epic branches start
from reviewed main; story branches start from the associated epic. Every PR
returns to its base: story to epic, final epic to main. Verify the actual source
revision and target instead of assuming that a similarly named branch is correct.

Explicit instructions can override the default for an identified edge case, such
as an integration synchronization, documentation-only route or separately approved
hotfix/release-staging flow. Record the instruction and actual base/target in the
issue/PR. Merely mentioning an alternative here is not an instruction to use it;
no override silently bypasses human review, merge or security requirements.

Keep stories small and independently reviewable, with matching code and canonical
documentation in the same PR. Every documentation code example added or changed
requires a unit test of that exact snippet or shared tested source. Syntax/lint
and link validation alone do not replace that test.

Production releases for Goal1 must be built from reviewed main, after integration,
and consumed through verified immutable source/build/artifact identities. An Epic
artifact does not become eligible merely because its commit later enters main.
Keep the Epic open through the main-release/live-deployment acceptance phase.

Choose the release version from the actual reviewed public-API change:
backward-incompatible changes increment MAJOR, backward-compatible functionality
increments MINOR, and backward-compatible bug fixes increment PATCH. Reset lower
components when incrementing MAJOR/MINOR. Agent suggestions are evidence for human
review, not authority to determine compatibility or issue a release. Initial 0.x
versions require an explicit compatibility policy; absence of a stable API does
not justify silently classifying a breaking fix as a patch.

Reserve the candidate version before creating its versioned branch. Branch/tag
collisions or a competing release require reconciliation and fresh approval; never
reuse a branch for another approved change or move an existing version tag.
Prerelease identifiers such as `1.5.0-rc.1` are optional reviewed candidates, not
production release tags. Immutable stable release tags are `vX.Y.Z`, pointing to
the exact reviewed and human-authorized main commit. Tagging/release publication
requires separate authenticated release approval after verified merge, bound to
the version and commit. This model does not authorize automatic deployment.

## Hotfixes

A verified hotfix ticket starts a separate process. An authenticated human approves
the scope and pinned released base; labels or urgency alone grant no authority.
The default path supports the latest released main version and a compatible patch.
For `v1.4.2`, the normal candidate is `hotfix/1.4.3`, targeting main and eventually
tagged `v1.4.3`. A feature or breaking change takes the normal release path instead.
Older supported lines require a separately approved maintenance policy; they must
not be guessed or merged indiscriminately into main.

Before branch creation, require main to equal the approved released base. Untagged
main changes, stale bases or concurrent release reservations hold for reconciliation
rather than contaminating a patch with unrelated work. Revalidate current scope,
branch/PR base and head, tests, completed review and human authority at publication,
merge and release boundaries. The shared webhook-driven review/remediation loop
and its two-attempt default cap apply to hotfixes as well.

After the patch tag is verified, track propagation PRs into affected active epic
and release branches. They require their own review/tests and human merge approval;
there is no develop branch to merge into. A changed base invalidates stale checks
and merge approval; changed plan/configuration pins require renewed plan approval.
Block further delivery from affected work until its required propagation is verified.
The hotfix process ends with the patch released and follow-ups tracked, not with
an assertion that every propagation PR has already merged.

For example, while `release/1.5.0` is being prepared, a `hotfix/1.4.3` can patch
released `v1.4.2` on main. Incorporate that verified patch into the active release
and affected epics before their next eligible publication/merge, re-run checks,
and obtain fresh approvals. Do not merge the unfinished `1.5.0` release into the
hotfix or tag the patch from an unapproved main head.

This is a project-specific adaptation of
[GitFlow's original branch model](https://nvie.com/posts/a-successful-git-branching-model/)
using [Semantic Versioning 2.0.0](https://semver.org/). GitFlow's develop branch is
intentionally omitted; SemVer specifies version meaning, not branch naming.
