#!/usr/bin/env python3
"""Read back the GitHub policy for skizzay/slickflow's main branch."""

import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys


REPOSITORY = "skizzay/slickflow"
REF = "refs/heads/main"
POLICY = Path(__file__).resolve().parents[1] / ".github/main-branch-protection.json"
REST_HEADERS = (
    "-H", "Accept: application/vnd.github+json",
    "-H", "X-GitHub-Api-Version: 2022-11-28",
)
RULE_QUERY = """
query {
  repository(owner: "skizzay", name: "slickflow") {
    ref(qualifiedName: "refs/heads/main") {
      branchProtectionRule {
        pattern
        lockBranch
        requiresDeployments
        branchProtectionRuleConflicts(first: 1) { totalCount }
        bypassPullRequestAllowances(first: 1) { totalCount }
        bypassForcePushAllowances(first: 1) { totalCount }
      }
    }
  }
}
"""


def github_api(*args):
    result = subprocess.run(
        ["gh", "api", "--hostname", "github.com", *args],
        capture_output=True, text=True, check=True, timeout=25,
    )
    return json.loads(result.stdout)


def check_value(actual, expected, name):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"unexpected {name}")


def verify():
    policy = json.loads(POLICY.read_text())
    protection_path = f"repos/{REPOSITORY}/branches/main/protection"
    protection = github_api(protection_path, *REST_HEADERS)
    check_value(protection["url"], f"https://api.github.com/{protection_path}", "protection URL")

    expected_checks = policy["required_status_checks"]
    checks = protection["required_status_checks"]
    check_value(checks["strict"], expected_checks["strict"], "strict required checks setting")
    actual = sorted(checks["checks"], key=lambda check: check["context"])
    check_value(len(actual), len(expected_checks["checks"]), "required check count")
    for check, expected in zip(actual, expected_checks["checks"]):
        check_value(check["context"], expected["context"], "required check name")
        check_value(check["app_id"], expected["app_id"], "required check GitHub App ID")
    check_value(
        sorted(checks["contexts"]), [check["context"] for check in expected_checks["checks"]],
        "required contexts",
    )
    reviews = protection["required_pull_request_reviews"]
    for name, expected in policy["required_pull_request_reviews"].items():
        check_value(reviews[name], expected, name)
    for name in ("enforce_admins", "allow_force_pushes", "allow_deletions", "required_conversation_resolution"):
        check_value(protection[name]["enabled"], policy[name], name)
    check_value(protection.get("restrictions"), policy["restrictions"], "push restrictions")

    result = github_api("graphql", "-f", f"query={RULE_QUERY}")
    if result.get("errors"):
        raise ValueError("GitHub GraphQL reported an error")
    rule = result["data"]["repository"]["ref"]["branchProtectionRule"]
    check_value(rule["pattern"], "main", "classic branch protection target")
    check_value(rule["lockBranch"], False, "branch lock")
    check_value(rule["requiresDeployments"], False, "required deployments")
    for name in ("branchProtectionRuleConflicts", "bypassPullRequestAllowances", "bypassForcePushAllowances"):
        check_value(rule[name]["totalCount"], 0, name)

    rulesets = github_api(
        f"repos/{REPOSITORY}/rulesets?includes_parents=true&targets=branch,push&per_page=1",
        *REST_HEADERS,
    )
    check_value(rulesets, [], "branch or push rulesets inventory; inspect repository rules")

    return {
        "repository": REPOSITORY,
        "ref": REF,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "classic_protection": policy,
        "overlapping_classic_rules": 0,
        "pull_request_bypass_actors": 0,
        "force_push_bypass_actors": 0,
        "branch_or_push_rulesets": 0,
    }


def main():
    try:
        print(json.dumps(verify(), indent=2))
    except subprocess.CalledProcessError as error:
        print(f"GitHub protection readback failed (gh exit {error.returncode}).", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("GitHub protection readback timed out.", file=sys.stderr)
        return 1
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"GitHub protection readback failed ({error}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
