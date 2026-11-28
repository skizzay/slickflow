import copy
import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_main_protection as verifier


PROTECTION_PATH = "repos/skizzay/slickflow/branches/main/protection"
GITHUB_PROTECTION = {
    "url": f"https://api.github.com/{PROTECTION_PATH}",
    "required_status_checks": {
        "strict": True,
        "contexts": ["Verify (arm64)", "Verify (amd64)"],
        "checks": [
            {"context": "Verify (arm64)", "app_id": 15368},
            {"context": "Verify (amd64)", "app_id": 15368},
        ],
    },
    "required_pull_request_reviews": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": False,
        "require_last_push_approval": False,
    },
    "enforce_admins": {"enabled": True},
    "allow_force_pushes": {"enabled": False},
    "allow_deletions": {"enabled": False},
    "required_conversation_resolution": {"enabled": True},
}
GITHUB_RULE = {
    "pattern": "main",
    "lockBranch": False,
    "requiresDeployments": False,
    "branchProtectionRuleConflicts": {"totalCount": 0},
    "bypassPullRequestAllowances": {"totalCount": 0},
    "bypassForcePushAllowances": {"totalCount": 0},
}


def github_graphql(rule):
    return {"data": {"repository": {"ref": {"branchProtectionRule": rule}}}}


class MainProtectionTest(unittest.TestCase):
    def test_read_only_calls_accept_the_repository_policy_and_return_evidence(self):
        responses = [GITHUB_PROTECTION, github_graphql(GITHUB_RULE), []]
        results = [subprocess.CompletedProcess([], 0, json.dumps(response)) for response in responses]
        with patch.object(verifier.subprocess, "run", side_effect=results) as run:
            evidence = verifier.verify()

        commands = [call.args[0] for call in run.call_args_list]
        self.assertTrue(all(call.kwargs["timeout"] == 25 for call in run.call_args_list))
        self.assertEqual([command[:4] for command in commands], [["gh", "api", "--hostname", "github.com"]] * 3)
        self.assertEqual(commands[0][4], PROTECTION_PATH)
        self.assertEqual(commands[1][4:6], ["graphql", "-f"])
        self.assertIn('ref(qualifiedName: "refs/heads/main")', commands[1][6])
        self.assertIn("query {", commands[1][6])
        self.assertEqual(
            commands[2][4],
            "repos/skizzay/slickflow/rulesets?includes_parents=true&targets=branch,push&per_page=1",
        )
        self.assertEqual(evidence["ref"], "refs/heads/main")
        self.assertEqual(evidence["repository"], "skizzay/slickflow")
        self.assertEqual(evidence["pull_request_bypass_actors"], 0)
        self.assertEqual(evidence["classic_protection"], json.loads(verifier.POLICY.read_text()))

    def test_missing_or_weaker_settings_reject_readback(self):
        mutations = (
            (("url",), "https://api.github.com/repos/other/slickflow/branches/main/protection"),
            (("enforce_admins", "enabled"), False),
            (("allow_force_pushes", "enabled"), True),
            (("allow_deletions", "enabled"), True),
            (("required_conversation_resolution", "enabled"), False),
            (("required_status_checks", "strict"), False),
            (("required_status_checks", "contexts"), ["Verify (amd64)"]),
            (("required_status_checks", "checks"), []),
            (("required_status_checks", "checks", 0, "app_id"), None),
            (("required_status_checks", "checks", 0, "app_id"), -1),
            (("required_status_checks", "checks", 0, "app_id"), 12),
            (("required_status_checks", "checks", 0, "app_id"), 15368.0),
            (("required_pull_request_reviews",), None),
            (("required_pull_request_reviews", "required_approving_review_count"), 1),
            (("required_pull_request_reviews", "required_approving_review_count"), False),
            (("required_pull_request_reviews", "dismiss_stale_reviews"), False),
            (("required_pull_request_reviews", "require_code_owner_reviews"), True),
            (("required_pull_request_reviews", "require_last_push_approval"), True),
        )
        for path, replacement in mutations:
            with self.subTest(path=path, replacement=replacement):
                protection = copy.deepcopy(GITHUB_PROTECTION)
                container = protection
                for key in path[:-1]:
                    container = container[key]
                container[path[-1]] = replacement
                self.assert_rejected(protection, github_graphql(GITHUB_RULE), [])

    def test_wrong_target_conflicts_bypasses_and_rulesets_reject_readback(self):
        mutations = {
            "pattern": "*",
            "lockBranch": True,
            "requiresDeployments": True,
            "branchProtectionRuleConflicts": {"totalCount": 1},
            "bypassPullRequestAllowances": {"totalCount": 1},
            "bypassForcePushAllowances": {"totalCount": 1},
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                rule = GITHUB_RULE | {field: replacement}
                self.assert_rejected(GITHUB_PROTECTION, github_graphql(rule), [])
        for status in ("active", "disabled", "evaluate"):
            with self.subTest(enforcement=status):
                self.assert_rejected(GITHUB_PROTECTION, github_graphql(GITHUB_RULE), [{"enforcement": status}])

    def test_failed_or_incomplete_api_reads_do_not_produce_evidence(self):
        failure = subprocess.CalledProcessError(1, ["gh"], stderr="sensitive process diagnostic")
        self.assert_rejected(failure)
        self.assert_rejected({})
        self.assert_rejected(GITHUB_PROTECTION, {"errors": [{"message": "partial query"}]})
        self.assert_rejected(GITHUB_PROTECTION, github_graphql(None))

    def test_readback_timeout_fails_without_printing_provider_output(self):
        failure = subprocess.TimeoutExpired(["gh"], 25, stderr="sensitive process diagnostic")
        self.assert_rejected(failure, message="GitHub protection readback timed out.")

    def assert_rejected(self, *responses, message="GitHub protection readback failed"):
        stdout, stderr = StringIO(), StringIO()
        with patch.object(verifier, "github_api", side_effect=responses), redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(verifier.main(), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn(message, stderr.getvalue())
        self.assertNotIn("sensitive process diagnostic", stderr.getvalue())
