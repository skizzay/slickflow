#!/usr/bin/env python3
"""Verify one reviewed SlickFlow release candidate using read-only provider evidence."""

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile
from zlib import error as CompressionError

import verify_main_protection
from control_plane_registry import BINDING_FIELD, BINDING_KEY, DIGEST, ROLES, Registry, RegistryError, is_digest


REPOSITORY = verify_main_protection.REPOSITORY
REF = verify_main_protection.REF
API = f"repos/{REPOSITORY}"
WEB = f"https://github.com/{REPOSITORY}"
REPOSITORY_ID = 1416953123
OWNER_ID = 972461
GITHUB_ACTIONS_APP = 15368
WORKFLOW = ".github/workflows/control-plane.yaml"
WORKFLOW_NAME = "Control-plane artifacts"
PUBLISH_SCRIPT = "scripts/publish-control-plane.sh"
POLICY = ".github/main-branch-protection.json"
ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    WORKFLOW, PUBLISH_SCRIPT, "scripts/publish_control_plane.py", "scripts/control_plane_registry.py", POLICY,
)
RUNNERS = {"amd64": "ubuntu-24.04", "arm64": "ubuntu-24.04-arm"}
IMAGE_MANIFESTS = {
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
}
MAX_RECEIPT = 16_384
MAX_ARCHIVE = 32_768
MAX_PROVENANCE = 4096
MAX_RESPONSE = 2_000_000
SHA = r"[0-9a-f]{40}"


class Rejected(Exception):
    """A rejection with a fixed, nonsecret diagnostic."""


def require(condition, message):
    if not condition:
        raise Rejected(message)


def expect(record, fields, message):
    require(isinstance(record, dict), message)
    require(
        all(type(record.get(key)) is type(value) and record[key] == value for key, value in fields.items()),
        message,
    )


def identifier(value, message):
    require(type(value) is int and 0 < value < 10**20, message)
    return value


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def instant(value):
    require(
        matches(value, r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)"),
        "Invalid evidence timestamp. Recheck the receipt and GitHub run.",
    )
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def command(args, message, size_limit=MAX_RESPONSE):
    try:
        result = subprocess.run(args, capture_output=True, check=True, timeout=25)
    except (OSError, subprocess.SubprocessError):
        raise Rejected(message) from None
    require(len(result.stdout) <= size_limit, message)
    return result.stdout


def json_object(data):
    def unique_fields(pairs):
        record = dict(pairs)
        if len(record) != len(pairs):
            raise ValueError("Duplicate JSON keys")
        return record

    record = json.loads(data, object_pairs_hook=unique_fields)
    if not isinstance(record, dict):
        raise ValueError("Expected JSON object")
    return record


def github_bytes(path, limit=MAX_RESPONSE):
    message = "GitHub evidence is unavailable. Check read access, Actions retention and connectivity, then retry."
    return command(
        ["gh", "api", "--hostname", "github.com", "--method", "GET", path, *verify_main_protection.REST_HEADERS],
        message, limit,
    )


def github(path):
    try:
        return json_object(github_bytes(path))
    except (ValueError, RecursionError):
        raise Rejected("GitHub returned unreadable evidence. Check API availability and retry.") from None


def verified_file(path, revision):
    content = (ROOT / path).read_bytes()
    blob = f"blob {len(content)}\0".encode() + content
    expect(
        github(f"{API}/contents/{path}?ref={revision}"),
        {"path": path, "type": "file", "sha": hashlib.sha1(blob).hexdigest()},
        f"Reviewed source differs at {path}. Reconcile the source with a trusted verifier checkout.",
    )


def read_receipt(path, pin, revision, configuration_revision, registry):
    if not matches(pin, DIGEST):
        raise Rejected("An independently authenticated owner receipt pin in sha256 format is required.")
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_RECEIPT + 1)
    except OSError:
        raise Rejected("The owner integration receipt is unavailable. Check the receipt file.") from None
    require(len(data) <= MAX_RECEIPT and digest(data) == pin,
            "The integration receipt does not match its trusted pin. Obtain the exact receipt from the owner.")
    receipt = json_object(data)
    expect(receipt, {
        "schema_version": 2, "repository": REPOSITORY, "ref": REF, "owner_id": OWNER_ID,
        "merge_sha": revision, "configuration_revision": configuration_revision,
        "protection_continuous_through_merge": True,
    }, "The owner receipt does not bind this exact integration and configuration.")
    registry.require_pin(receipt.get(BINDING_FIELD))
    for field in ("head_sha", "base_sha", "policy_revision"):
        require(matches(receipt.get(field), SHA), "The receipt requires full head, base and policy revisions.")
    for field in ("pr_number", "native_run_id", "native_attempt"):
        identifier(receipt.get(field), "The receipt requires the PR, native run and attempt IDs.")
    expected_policy = json_object((ROOT / POLICY).read_bytes())
    readback_times = []
    for field in ("premerge_protection", "postmerge_protection"):
        protection = receipt[field]
        expect(protection, {
            "repository": REPOSITORY, "ref": REF, "overlapping_classic_rules": 0,
            "pull_request_bypass_actors": 0, "force_push_bypass_actors": 0, "branch_or_push_rulesets": 0,
        }, "The receipt requires successful main protection readback before and after the merge.")
        # Compare JSON representations so booleans cannot stand in for numbers.
        require(
            json.dumps(protection["classic_protection"], sort_keys=True)
            == json.dumps(expected_policy, sort_keys=True),
            "The receipt's protection readback differs from the approved policy.",
        )
        readback_times.append(instant(protection["verified_at"]))
    before, after = readback_times
    approved_at = instant(receipt["approved_at"])
    merged_at = instant(receipt["merged_at"])
    require(
        before <= approved_at < merged_at <= after <= datetime.now(timezone.utc),
        "The receipt must show policy readback, owner approval, merge and repeat readback in that order.",
    )
    return receipt


def verify_workflow_run(run, run_id, workflow_id, revision, branch, events):
    message = "The selected run has the wrong repository, workflow, source event, branch or revision."
    expect(run, {
        "id": run_id, "workflow_id": workflow_id, "name": WORKFLOW_NAME, "path": WORKFLOW,
        "head_sha": revision, "head_branch": branch,
    }, message)
    for field in ("repository", "head_repository"):
        expect(run[field], {"full_name": REPOSITORY, "id": REPOSITORY_ID}, message)
    require(run.get("event") in events, message)
    expect(run, {"status": "completed", "conclusion": "success"},
           "The selected workflow attempt must finish successfully. Inspect its current Actions status.")
    return identifier(run.get("run_attempt"), "GitHub did not identify the current workflow attempt.")


def verify_jobs(run_id, attempt, revision, branch, publication):
    endpoint = f"{API}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=20"
    result = github(endpoint)
    jobs = result["jobs"]
    require(isinstance(jobs, list) and len(jobs) <= 20 and result["total_count"] == len(jobs),
            "GitHub returned an incomplete list of jobs for the selected attempt.")
    required = {f"Verify ({arch})": runner for arch, runner in RUNNERS.items()}
    if publication:
        required.update({f"Publish ({arch})": runner for arch, runner in RUNNERS.items()})
        required["Check publication source"] = "ubuntu-24.04"
    verified = {}
    for name, runner in required.items():
        matches_for_job = [job for job in jobs if job.get("name") == name]
        message = f"{name} must succeed in the selected attempt. Inspect Actions and rerun all jobs if needed."
        require(len(matches_for_job) == 1, message)
        job = matches_for_job[0]
        expect(job, {
            "run_id": run_id, "run_attempt": attempt, "head_sha": revision, "head_branch": branch,
            "workflow_name": WORKFLOW_NAME, "labels": [runner], "status": "completed", "conclusion": "success",
        }, message)
        identifier(job.get("id"), message)
        verified[name] = job
    return verified


def verify_integration(receipt, workflow_id):
    pr_number = receipt["pr_number"]
    head = receipt["head_sha"]
    base = receipt["base_sha"]
    revision = receipt["merge_sha"]
    pr = github(f"{API}/pulls/{pr_number}")
    message = "GitHub did not confirm the exact owner-merged pull request into main."
    expect(pr, {"number": pr_number, "state": "closed", "merged": True, "merge_commit_sha": revision}, message)
    require(instant(pr["merged_at"]) == instant(receipt["merged_at"]), message)
    expect(pr["merged_by"], {"id": OWNER_ID, "type": "User"}, message)
    expect(pr["base"], {"ref": "main"}, message)
    expect(pr["base"]["repo"], {"id": REPOSITORY_ID, "full_name": REPOSITORY}, message)
    expect(pr["head"], {"sha": head}, message)
    expect(pr["head"]["repo"], {"id": REPOSITORY_ID, "full_name": REPOSITORY}, message)

    commit = github(f"{API}/git/commits/{revision}")
    message = "Use an owner-reviewed GitHub merge commit with the approved base and head as its two parents."
    expect(commit, {"sha": revision}, message)
    require([parent["sha"] for parent in commit["parents"]] == [base, head], message)

    main = github(f"{API}/git/ref/heads/main")
    message = "GitHub did not confirm that the exact integrated revision remains on main."
    expect(main, {"ref": REF}, message)
    expect(main["object"], {"type": "commit"}, message)
    main_sha = main["object"]["sha"]
    require(matches(main_sha, SHA), message)
    compare = github(f"{API}/compare/{revision}...{main_sha}?per_page=1")
    require(compare.get("status") in ("identical", "ahead"), message)
    expect(compare["base_commit"], {"sha": revision}, message)
    expect(compare["merge_base_commit"], {"sha": revision}, message)

    native_run_id = receipt["native_run_id"]
    native_attempt = receipt["native_attempt"]
    native = github(f"{API}/actions/runs/{native_run_id}")
    branch = pr["head"]["ref"]
    require(isinstance(branch, str) and branch, "GitHub did not identify the integrated PR head branch.")
    current = verify_workflow_run(native, native_run_id, workflow_id, head, branch, ("pull_request",))
    require(current == native_attempt,
            "The approved PR checks are no longer the run's current attempt. Reconcile the integration evidence.")
    associated_prs = native["pull_requests"]
    require(isinstance(associated_prs, list), "GitHub returned invalid PR associations for native checks.")
    if associated_prs:
        approved = [item for item in associated_prs if item.get("number") == pr_number]
        require(len(approved) == 1, "GitHub's PR association conflicts with the owner receipt.")
        expect(approved[0]["base"], {"ref": "main", "sha": base}, "GitHub's PR check base conflicts with the receipt.")
        expect(approved[0]["head"], {"ref": branch, "sha": head}, "GitHub's PR check head conflicts with the receipt.")
    jobs = verify_jobs(native_run_id, native_attempt, head, branch, publication=False)
    suite_id = identifier(native.get("check_suite_id"), "GitHub did not identify the PR check suite.")
    approved_at = instant(receipt["approved_at"])
    for name, job in jobs.items():
        require(instant(job["completed_at"]) <= approved_at,
                "The owner approval predates the successful native PR checks.")
        job_id = job["id"]
        check = github(f"{API}/check-runs/{job_id}")
        message = "GitHub did not confirm a required check published by the GitHub Actions app."
        expect(check, {"id": job_id, "name": name, "head_sha": head, "status": "completed", "conclusion": "success"}, message)
        expect(check["app"], {"id": GITHUB_ACTIONS_APP}, message)
        expect(check["check_suite"], {"id": suite_id}, message)
    verified_file(WORKFLOW, head)
    verified_file(POLICY, receipt["policy_revision"])
    return branch


def read_provenance(run_id, attempt, arch, revision, publisher, registry):
    name = f"control-plane-provenance-{arch}-{attempt}"
    response = github(f"{API}/actions/runs/{run_id}/artifacts?name={name}&per_page=2")
    message = f"GitHub must provide one current {arch} provenance artifact. Check Actions retention and attempt."
    artifacts = response["artifacts"]
    require(response["total_count"] == 1 and isinstance(artifacts, list) and len(artifacts) == 1, message)
    artifact = artifacts[0]
    expect(artifact, {"name": name, "expired": False}, message)
    expect(artifact["workflow_run"], {
        "id": run_id, "repository_id": REPOSITORY_ID, "head_repository_id": REPOSITORY_ID,
        "head_branch": "main", "head_sha": revision,
    }, message)
    require(instant(publisher["started_at"]) <= instant(artifact["created_at"]) <= instant(publisher["completed_at"]),
            f"The {arch} provenance was not uploaded during its publication job.")
    artifact_id = identifier(artifact.get("id"), message)
    size = identifier(artifact.get("size_in_bytes"), message)
    require(size <= MAX_ARCHIVE and matches(artifact.get("digest"), DIGEST), message)
    archive = github_bytes(f"{API}/actions/artifacts/{artifact_id}/zip", MAX_ARCHIVE)
    require(len(archive) == size and digest(archive) == artifact["digest"],
            f"The {arch} provenance archive differs from GitHub's digest. Check Actions and retry.")
    try:
        with ZipFile(BytesIO(archive)) as bundle:
            entries = bundle.infolist()
            require(
                len(entries) == 1 and entries[0].filename == f"provenance-{arch}.json"
                and 0 < entries[0].file_size <= MAX_PROVENANCE
                and entries[0].compress_type in (ZIP_DEFLATED, ZIP_STORED),
                f"The {arch} provenance archive has unexpected contents.",
            )
            with bundle.open(entries[0]) as member:
                provenance = json_object(member.read(MAX_PROVENANCE + 1))
    except (BadZipFile, CompressionError, OSError, RuntimeError, ValueError):
        raise Rejected(f"The {arch} provenance archive is unreadable. Check the published artifact.") from None
    expect(provenance, {
        "revision": revision, "architecture": arch, "run_url": f"{WEB}/actions/runs/{run_id}",
        "run_attempt": str(attempt),
    }, f"The {arch} provenance does not match the exact run, attempt, platform and revision.")
    registry.require_pin(provenance.get(BINDING_FIELD))
    images = provenance["images"]
    require(isinstance(images, dict) and images.keys() == set(ROLES),
            f"The {arch} provenance must contain exactly one runtime and migration pair.")
    require(all(is_digest(value) for value in images.values()),
            f"The {arch} provenance must contain only immutable Forgejo manifest digests.")
    require(images["runtime"] != images["migration"],
            f"The {arch} provenance must contain different runtime and migration digests.")
    return artifact_id, images


def verify_registry_image(registry, manifest_digest, role, arch, revision):
    reference = registry.reference(role, manifest_digest)
    message = f"Forgejo {arch} {role} evidence is unavailable. Check Docker Buildx, read access and connectivity, then retry."
    inspect = ["docker", "buildx", "imagetools", "inspect"]
    manifest_bytes = command([*inspect, "--raw", reference], message)
    require(
        digest(manifest_bytes) == manifest_digest
        or (manifest_bytes.endswith(b"\n") and digest(manifest_bytes[:-1]) == manifest_digest),
        f"The Forgejo {arch} {role} manifest does not match its immutable digest.",
    )
    manifest = json_object(manifest_bytes)
    invalid_manifest = f"Select a single-platform image manifest for Forgejo {arch} {role}."
    expect(manifest, {"schemaVersion": 2}, invalid_manifest)
    require(manifest.get("mediaType") in IMAGE_MANIFESTS, invalid_manifest)
    image = json_object(command([*inspect, "--format", "{{json .Image}}", reference], message))
    expect(image, {"os": "linux", "architecture": arch},
           f"The Forgejo {role} image platform does not match linux/{arch}.")
    expect(image["config"]["Labels"], {
        "org.opencontainers.image.source": WEB, "org.opencontainers.image.revision": revision,
    }, f"The Forgejo {arch} {role} image source or revision label differs from the approved source.")


def verify_candidate(run_id, revision, configuration_revision, receipt_path, pin):
    identifier(run_id, "Choose a positive numeric GitHub Actions run ID.")
    require(matches(revision, SHA) and matches(configuration_revision, SHA),
            "Use full lowercase Git revisions for the source and deployment configuration.")
    registry = Registry.parse(os.environ.get(BINDING_KEY))
    receipt = read_receipt(receipt_path, pin, revision, configuration_revision, registry)
    repository = github(API)
    expect(repository, {"id": REPOSITORY_ID, "full_name": REPOSITORY}, "GitHub repository identity differs.")
    expect(repository["owner"], {"id": OWNER_ID, "login": "skizzay", "type": "User"}, "GitHub owner identity differs.")
    workflow = github(f"{API}/actions/workflows/control-plane.yaml")
    expect(workflow, {"name": WORKFLOW_NAME, "path": WORKFLOW}, "GitHub workflow identity differs.")
    workflow_id = identifier(workflow.get("id"), "GitHub did not identify the control-plane workflow.")
    run_path = f"{API}/actions/runs/{run_id}"
    run = github(run_path)
    events = ("push", "workflow_dispatch")
    attempt = verify_workflow_run(run, run_id, workflow_id, revision, "main", events)
    for path in SOURCE_FILES:
        verified_file(path, revision)
    require(instant(run["created_at"]) >= instant(receipt["merged_at"]),
            "The selected build predates reviewed integration. Select a new main-built run.")
    pr_branch = verify_integration(receipt, workflow_id)
    jobs = verify_jobs(run_id, attempt, revision, "main", publication=True)
    platforms = {}
    for arch in RUNNERS:
        artifact_id, images = read_provenance(run_id, attempt, arch, revision, jobs[f"Publish ({arch})"], registry)
        platforms[f"linux/{arch}"] = {"provenance_artifact_id": artifact_id, **images}
    for arch in RUNNERS:
        for role in ROLES:
            verify_registry_image(registry, platforms[f"linux/{arch}"][role], role, arch, revision)

    try:
        protection = verify_main_protection.verify()
    except (OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
        raise Rejected("Main protection readback failed. Check GitHub administration read access and reconcile settings.") from None
    native_id = receipt["native_run_id"]
    latest_native = github(f"{API}/actions/runs/{native_id}")
    require(
        verify_workflow_run(latest_native, native_id, workflow_id, receipt["head_sha"], pr_branch, ("pull_request",))
        == receipt["native_attempt"],
        "The approved PR check attempt changed during verification. Reconcile the integration evidence.",
    )
    latest = github(run_path)
    require(
        verify_workflow_run(latest, run_id, workflow_id, revision, "main", events) == attempt
        and latest["event"] == run["event"],
        "The main workflow attempt changed during verification. Retry with the current complete attempt.",
    )
    return {
        "schema_version": 2,
        BINDING_FIELD: registry.binding_sha256,
        "repository": REPOSITORY,
        "source_revision": revision,
        "configuration_revision": configuration_revision,
        "ref": REF,
        "event": run["event"],
        "workflow": WORKFLOW,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "run_url": f"{WEB}/actions/runs/{run_id}",
        "run_attempt": attempt,
        "job_ids": {name: job["id"] for name, job in jobs.items()},
        "platforms": platforms,
        "integration": {
            "pull_request": f"{WEB}/pull/{receipt['pr_number']}",
            "head_sha": receipt["head_sha"],
            "base_sha": receipt["base_sha"],
            "owner_id": OWNER_ID,
            "approved_at": receipt["approved_at"],
            "merged_at": receipt["merged_at"],
            "native_run_id": receipt["native_run_id"],
            "native_run_attempt": receipt["native_attempt"],
            "policy_revision": receipt["policy_revision"],
            "trusted_receipt_digest": pin,
            "premerge_protection_verified_at": receipt["premerge_protection"]["verified_at"],
            "postmerge_protection_verified_at": receipt["postmerge_protection"]["verified_at"],
            "protection_verified_at": protection["verified_at"],
        },
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


class CandidateArguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Invalid candidate options. Use --help for the required inputs.\n")


def main(argv=None):
    parser = CandidateArguments(description=__doc__)
    parser.add_argument("--run-id", required=True, type=int, help="GitHub Actions run ID")
    parser.add_argument("--source-revision", required=True, help="Exact reviewed main merge commit")
    parser.add_argument("--configuration-revision", required=True, help="Exact deployment configuration revision")
    parser.add_argument("--integration-receipt", required=True, type=Path, help="Owner's integration evidence JSON file")
    parser.add_argument("--trusted-receipt-digest", required=True, help="Receipt SHA-256 pin acquired independently from the owner")
    args = parser.parse_args(argv)
    try:
        record = verify_candidate(
            args.run_id, args.source_revision, args.configuration_revision,
            args.integration_receipt, args.trusted_receipt_digest,
        )
    except (Rejected, RegistryError) as error:
        print(f"Candidate rejected. {error}", file=sys.stderr)
        return 1
    except (OSError, KeyError, TypeError, ValueError, AttributeError, RecursionError):
        print("Candidate rejected. Evidence is malformed or incomplete. Check the receipt and provider responses.",
              file=sys.stderr)
        return 1
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
