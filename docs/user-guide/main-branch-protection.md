# SlickFlow main branch protection

[Story #142](https://github.com/skizzay/slickflow/issues/142) targets `main` in
`skizzay/slickflow` with one classic GitHub branch protection rule. Public
repositories on GitHub Free support this rule. The owner chose a zero-review-count
rule for the current solo-maintainer model. The [policy file](../../.github/main-branch-protection.json)
is active on `main` following owner-authorized activation and independent
readback under #142. Equivalent disposable-branch tests verified rejection of
direct/force/delete requests and pending, failed and missing required checks;
checked integration succeeded. The test branches were removed afterward. Run the
verifier again before integration; recorded evidence does not certify future
settings or earlier main commits. The
[branching contract](../requirements/branching-and-versioning.md) governs story,
Epic and release approvals.

## Normal integration after activation

GitHub requires a pull request targeting `main`, resolved review conversations,
and the up-to-date `Verify (amd64)` and `Verify (arm64)` checks. Both use the
GitHub Actions app ID `15368` from [control-plane CI](control-plane-ci.md). The
rule applies to administrators and blocks direct updates without a PR, force
pushes and branch deletion. The policy grants zero bypass allowances. It requires zero GitHub
approving reviews, dismisses stale review approvals, and leaves code-owner and
last-push approval requirements off. A positive GitHub review count would require
an eligible independent reviewer for a PR the owner authors.

The owner reviews the exact PR head and current main base, confirms both native
jobs succeeded for the current candidate, records approval tied to those revisions,
and merges manually. Repeat validation and obtain fresh approval if the head or base
changes. Request Copilot review through GitHub and consider its findings as part of
review. Explicit human approval is mandatory even with completed automated review.
GitHub permits successful, skipped and neutral results for required checks. For
SlickFlow approval, require actual successful native jobs from the approved
`Control-plane artifacts` workflow. The branch rule identifies their check names
and publishing app, so inspect changes to that workflow and job naming in review.
[GitHub required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)

## Apply and verify

Before application, review the current rule and actor inventory. If live settings
have changed, reconcile them with the owner. The repository owner authorizes the
exact settings change independently of approving the implementation PR. An
authorized administrator applies the [policy file](../../.github/main-branch-protection.json)
to the single `main` branch via the [GitHub branch-protection update endpoint](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection).
The reviewed policy can be applied from the story or Epic revision before the
Epic integrates into main.

After application, run the [read-only verifier](../../scripts/verify_main_protection.py)
with Python 3 and GitHub CLI authenticated to github.com with repository
administration read access. It verifies the exact classic target and settings,
checks for classic rule conflicts and PR/force-push bypasses, and flags any branch
or push ruleset, including disabled ones, for reconciliation. Save its timestamped,
nonsecret JSON as protection evidence. A mismatch or failed read requires
reconciliation before integration. The test suite compares the policy to
GitHub-shaped fixtures and exercises rejected settings and response failures.

Keep server enforcement tests on a separately authorized disposable branch with
the same rule and explicitly approved test setup. Capture GitHub's decisions for
non-PR, force-push and delete requests, PRs with failed or missing required checks,
and a PR with both successful current checks and recorded owner review. The
production workflow validates PRs to `main` and `epic/*`, so use an approved
`epic/*` test target for equivalent check observations. Dry runs and fixture tests
establish readback behavior. Provider attempt outcomes on the disposable branch
and actual main policy readback are separate pieces of evidence.

Before the release-candidate Epic enters main, capture effective protection and
reviewed integration evidence. Preserve the policy revision and verification
time, PR link, exact head and base/merge candidate, native check conclusions and
run/attempt links, explicit owner approval, and resulting main commit. Repeat
readback at release verification and reconcile intervening changes. These records
serve [release verification #136](https://github.com/skizzay/slickflow/issues/136)
and [publication #139](https://github.com/skizzay/slickflow/issues/139). Evidence
must show protection already in effect for the candidate's integration.

## Emergency restoration

The owner retains settings administration. For a time-critical repository recovery
or security response, the owner can separately authorize a temporary policy change.
Record the reason, executing administrator, allowed operation and exact ref or
revision, minimal setting change, and restoration deadline in the incident record
before any change. Restore the approved policy immediately after the action or by
that deadline, whichever comes first, and run the verifier. Record the before and
after settings, actions and resulting refs, restoration evidence, and owner
post-use review. Hold ordinary integration and release during the exception and
reconcile any affected candidate through the normal approval path.
