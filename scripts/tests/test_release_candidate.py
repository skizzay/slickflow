from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_release_candidate as verifier


API = verifier.API
WEB = verifier.WEB
WORKFLOW_ID = 419651051
RUN_ID = 46070000001
NATIVE_RUN_ID = 46070000002
ATTEMPT = 2
PR = 150
SOURCE = "a" * 40
HEAD = "b" * 40
BASE = "c" * 40
CONFIGURATION = "d" * 40
POLICY_REVISION = "e" * 40
CURRENT_MAIN = "f" * 40
PR_BRANCH = "epic/128"
RUN_PATH = f"{API}/actions/runs/{RUN_ID}"
NATIVE_PATH = f"{API}/actions/runs/{NATIVE_RUN_ID}"
JOBS = f"{RUN_PATH}/attempts/{ATTEMPT}/jobs?per_page=20"
PR_JOBS = f"{NATIVE_PATH}/attempts/1/jobs?per_page=20"
PR_RUN_STARTED = "2024-11-27T18:00:00Z"
PR_JOBS_COMPLETED = "2024-11-27T18:10:00Z"
POLICY_CHECKED = "2024-11-27T18:12:00Z"
APPROVED = "2024-11-27T18:15:00Z"
MERGED = "2024-11-27T18:16:00Z"
POST_MERGE_READBACK = "2024-11-27T18:16:15Z"
BUILD_STARTED = "2024-11-27T18:17:00Z"
BUILD_PUBLISHED = "2024-11-27T18:28:00Z"
BUILD_COMPLETE = "2024-11-27T18:29:00Z"
SECRET = "sensitive-upstream-diagnostic"
ARTIFACT_IDS = {"amd64": 901, "arm64": 902}
RUNNER = {"amd64": "ubuntu-24.04", "arm64": "ubuntu-24.04-arm"}
REPO = {"id": verifier.REPOSITORY_ID, "full_name": verifier.REPOSITORY}


def github_run(run_id, revision, event, branch, attempt, created_at):
    return {
        "id": run_id, "workflow_id": WORKFLOW_ID, "name": verifier.WORKFLOW_NAME, "path": verifier.WORKFLOW,
        "event": event, "head_branch": branch, "head_sha": revision, "created_at": created_at,
        "status": "completed", "conclusion": "success", "run_attempt": attempt, "check_suite_id": 12000,
        "repository": REPO, "head_repository": REPO, "pull_requests": [], "unused_secret": SECRET,
    }


def github_job(job_id, name, run, runner, completed_at):
    return {
        "id": job_id, "name": name, "run_id": run["id"], "run_attempt": run["run_attempt"],
        "head_branch": run["head_branch"], "head_sha": run["head_sha"], "workflow_name": run["name"],
        "status": "completed", "conclusion": "success", "labels": [runner], "started_at": run["created_at"],
        "completed_at": completed_at,
    }


def protection(verified_at):
    return {
        "repository": verifier.REPOSITORY, "ref": verifier.REF, "verified_at": verified_at,
        "classic_protection": json.loads((ROOT / verifier.POLICY).read_bytes()),
        "overlapping_classic_rules": 0, "pull_request_bypass_actors": 0,
        "force_push_bypass_actors": 0, "branch_or_push_rulesets": 0,
    }


class ReleaseCandidateTest(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.receipt_path = Path(self.directory.name) / "receipt.json"
        self.receipt = {
            "schema_version": 1, "repository": verifier.REPOSITORY, "ref": verifier.REF,
            "owner_id": verifier.OWNER_ID, "pr_number": PR, "head_sha": HEAD, "base_sha": BASE,
            "merge_sha": SOURCE, "approved_at": APPROVED, "merged_at": MERGED,
            "configuration_revision": CONFIGURATION, "protection_continuous_through_merge": True,
            "premerge_protection": protection(POLICY_CHECKED),
            "postmerge_protection": protection(POST_MERGE_READBACK),
            "policy_revision": POLICY_REVISION, "native_run_id": NATIVE_RUN_ID, "native_attempt": 1,
            "unused_secret": SECRET,
        }
        self.enroll_fixture_receipt()
        run = github_run(RUN_ID, SOURCE, "push", "main", ATTEMPT, BUILD_STARTED)
        native = github_run(NATIVE_RUN_ID, HEAD, "pull_request", PR_BRANCH, 1, PR_RUN_STARTED)
        native_jobs = [github_job(i, f"Verify ({arch})", native, runner, PR_JOBS_COMPLETED)
                       for i, (arch, runner) in enumerate(RUNNER.items(), start=301)]
        main_jobs = [github_job(100, "Check publication source", run, RUNNER["amd64"], BUILD_COMPLETE)]
        for i, (arch, runner) in enumerate(RUNNER.items(), start=101):
            main_jobs.extend([
                github_job(i, f"Verify ({arch})", run, runner, BUILD_COMPLETE),
                github_job(i + 100, f"Publish ({arch})", run, runner, BUILD_COMPLETE),
            ])
        self.github_responses = {
            API: REPO | {"owner": {"id": verifier.OWNER_ID, "login": "skizzay", "type": "User"}},
            f"{API}/actions/workflows/control-plane.yaml": {
                "id": WORKFLOW_ID, "name": verifier.WORKFLOW_NAME, "path": verifier.WORKFLOW,
            },
            RUN_PATH: run,
            NATIVE_PATH: native,
            JOBS: {"total_count": len(main_jobs), "jobs": main_jobs},
            PR_JOBS: {"total_count": len(native_jobs), "jobs": native_jobs},
            f"{API}/pulls/{PR}": {
                "number": PR, "merged": True, "state": "closed", "merge_commit_sha": SOURCE,
                "merged_at": MERGED, "merged_by": {"id": verifier.OWNER_ID, "type": "User"},
                "head": {"ref": PR_BRANCH, "sha": HEAD, "repo": REPO},
                "base": {"ref": "main", "sha": CURRENT_MAIN, "repo": REPO},
            },
            f"{API}/git/commits/{SOURCE}": {"sha": SOURCE, "parents": [{"sha": BASE}, {"sha": HEAD}]},
            f"{API}/git/ref/heads/main": {"ref": verifier.REF, "object": {"sha": CURRENT_MAIN, "type": "commit"}},
            f"{API}/compare/{SOURCE}...{CURRENT_MAIN}?per_page=1": {
                "status": "ahead", "merge_base_commit": {"sha": SOURCE}, "base_commit": {"sha": SOURCE},
            },
        }
        for job in native_jobs:
            self.github_responses[f"{API}/check-runs/{job['id']}"] = job | {
                "app": {"id": 15368}, "check_suite": {"id": native["check_suite_id"]},
            }
        for path, revision in (
            (verifier.WORKFLOW, SOURCE), (verifier.PUBLISH_SCRIPT, SOURCE), (verifier.POLICY, SOURCE),
            (verifier.WORKFLOW, HEAD), (verifier.POLICY, POLICY_REVISION),
        ):
            data = (ROOT / path).read_bytes()
            sha = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            self.github_responses[f"{API}/contents/{path}?ref={revision}"] = {"path": path, "type": "file", "sha": sha}
        self.manifests = {}
        self.images = {}
        self.provenance = {}
        self.archives = {}
        for arch in RUNNER:
            images = {}
            for role in ("runtime", "migration"):
                manifest = json.dumps({
                    "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "layers": [{"digest": verifier.digest(f"{role}-{arch}".encode())}],
                }).encode()
                reference = f"ghcr.io/{verifier.REPOSITORY}-{role}@{verifier.digest(manifest)}"
                self.manifests[reference] = manifest
                self.images[reference] = {
                    "os": "linux", "architecture": arch,
                    "config": {"Labels": {
                        "org.opencontainers.image.source": WEB, "org.opencontainers.image.revision": SOURCE,
                        "private_unused_label": SECRET,
                    }},
                }
                images[role] = reference
            self.provenance[arch] = {
                "revision": SOURCE, "architecture": arch, "run_url": f"{WEB}/actions/runs/{RUN_ID}",
                "run_attempt": str(ATTEMPT), "images": images,
            }
            self.build_archive(arch)
        self.attempt_reads = {}
        self.rerun = None
        self.command_mock = self.enterContext(patch.object(verifier.subprocess, "run", side_effect=self.command))
        self.check_current_protection = self.enterContext(
            patch.object(verifier.verify_main_protection, "verify", return_value=protection(POST_MERGE_READBACK))
        )

    def enroll_fixture_receipt(self):
        content = json.dumps(self.receipt).encode()
        self.receipt_path.write_bytes(content)
        self.pin = verifier.digest(content)

    def artifact_path(self, arch):
        return (f"{RUN_PATH}/artifacts?name=control-plane-provenance-{arch}-{ATTEMPT}&per_page=2")

    def artifact(self, arch):
        return self.github_responses[self.artifact_path(arch)]["artifacts"][0]

    def build_archive(self, arch, extra_file=False, compression=ZIP_DEFLATED):
        archive = BytesIO()
        with ZipFile(archive, "w", compression=compression) as bundle:
            bundle.writestr(f"provenance-{arch}.json", json.dumps(self.provenance[arch]))
            if extra_file:
                bundle.writestr("unknown.json", "{}")
        artifact_id = ARTIFACT_IDS[arch]
        data = archive.getvalue()
        self.archives[f"{API}/actions/artifacts/{artifact_id}/zip"] = data
        self.github_responses[self.artifact_path(arch)] = {"total_count": 1, "artifacts": [{
            "id": artifact_id, "size_in_bytes": len(data), "digest": verifier.digest(data),
            "expired": False, "name": f"control-plane-provenance-{arch}-{ATTEMPT}", "created_at": BUILD_PUBLISHED,
            "workflow_run": {
                "id": RUN_ID, "repository_id": verifier.REPOSITORY_ID, "head_repository_id": verifier.REPOSITORY_ID,
                "head_branch": "main", "head_sha": SOURCE,
            },
        }]}

    def command(self, args, **options):
        self.assertEqual(options, {"capture_output": True, "check": True, "timeout": 25})
        if args[0] == "gh":
            self.assertEqual(args[:6], ["gh", "api", "--hostname", "github.com", "--method", "GET"])
            path = args[6]
            if path in self.archives:
                output = self.archives[path]
            else:
                response = self.github_responses[path]
                if isinstance(response, Exception):
                    raise response
                self.attempt_reads[path] = self.attempt_reads.get(path, 0) + 1
                if path == self.rerun and self.attempt_reads[path] > 1:
                    response = response | {"run_attempt": response["run_attempt"] + 1}
                output = json.dumps(response).encode()
        else:
            self.assertEqual(args[:4], ["docker", "buildx", "imagetools", "inspect"])
            reference = args[-1]
            if args[4] == "--raw":
                output = self.manifests[reference]
            else:
                self.assertEqual(args[4:6], ["--format", "{{json .Image}}"])
                output = json.dumps(self.images[reference]).encode()
            if isinstance(output, Exception):
                raise output
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr=b"")

    def cli(self):
        arguments = [
            "--run-id", str(RUN_ID), "--source-revision", SOURCE, "--configuration-revision", CONFIGURATION,
            "--integration-receipt", str(self.receipt_path), "--trusted-receipt-digest", self.pin,
        ]
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = verifier.main(arguments)
        return status, stdout.getvalue(), stderr.getvalue()

    def assert_rejected(self, message):
        status, stdout, stderr = self.cli()
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn(message, stderr)
        self.assertNotIn(SECRET, stderr)

    def test_verified_candidate_binds_exact_attempt_digest_pairs_and_configuration(self):
        # Buildx versions that append a newline report the same manifest content.
        reference = self.provenance["arm64"]["images"]["runtime"]
        self.manifests[reference] += b"\n"
        status, stdout, stderr = self.cli()
        self.assertEqual((status, stderr), (0, ""))
        record = json.loads(stdout)
        self.assertEqual(record["repository"], "skizzay/slickflow")
        self.assertEqual(record["ref"], "refs/heads/main")
        self.assertEqual(record["source_revision"], SOURCE)
        self.assertEqual(record["configuration_revision"], CONFIGURATION)
        self.assertEqual(record["run_id"], RUN_ID)
        self.assertEqual(record["run_attempt"], ATTEMPT)
        self.assertEqual(record["integration"]["base_sha"], BASE)
        self.assertEqual(record["integration"]["head_sha"], HEAD)
        self.assertEqual(record["integration"]["trusted_receipt_digest"], self.pin)
        self.assertEqual(record["job_ids"]["Publish (arm64)"], 202)
        for arch, platform in record["platforms"].items():
            cpu = arch.split("/")[1]
            self.assertEqual(platform, {"provenance_artifact_id": ARTIFACT_IDS[cpu], **self.provenance[cpu]["images"]})
        self.assertEqual(self.attempt_reads[RUN_PATH], 2)
        self.assertEqual(self.attempt_reads[NATIVE_PATH], 2)
        self.check_current_protection.assert_called_once()
        self.assertNotIn(SECRET, stdout)

    def test_branch_and_wrong_workflow_run_are_rejected_even_for_integrated_sha(self):
        run = self.github_responses[RUN_PATH]
        for field, replacement in (
            ("head_branch", "epic/128"), ("event", "pull_request"), ("path", ".github/workflows/lookalike.yaml"),
            ("workflow_id", WORKFLOW_ID + 1), ("head_sha", HEAD),
            ("head_repository", {"full_name": verifier.REPOSITORY, "id": verifier.REPOSITORY_ID + 1}),
        ):
            with self.subTest(field=field):
                self.github_responses[RUN_PATH] = run | {field: replacement}
                self.assert_rejected("wrong repository, workflow, source event, branch or revision")

    def test_reviewed_workflow_and_ref_guard_are_required_for_release_proof(self):
        self.github_responses[RUN_PATH]["event"] = "workflow_dispatch"
        for path in (verifier.WORKFLOW, verifier.PUBLISH_SCRIPT):
            with self.subTest(path=path):
                expected = self.github_responses[f"{API}/contents/{path}?ref={SOURCE}"]
                original = expected["sha"]
                expected["sha"] = HEAD
                self.assert_rejected(f"Reviewed source differs at {path}")
                expected["sha"] = original

    def test_protection_receipt_cannot_be_self_asserted_or_bound_to_other_config(self):
        self.receipt["configuration_revision"] = HEAD
        self.receipt_path.write_bytes(json.dumps(self.receipt).encode())
        self.assert_rejected("does not match its trusted pin")
        self.enroll_fixture_receipt()
        self.assert_rejected("does not bind this exact integration and configuration")
        self.command_mock.assert_not_called()

    def test_historical_protection_and_approval_order_are_required(self):
        original = deepcopy(self.receipt)
        for field, replacement in (
            ("premerge_protection", protection(BUILD_COMPLETE)), ("postmerge_protection", protection(APPROVED)),
            ("postmerge_protection", protection("2999-01-01T00:00:00Z")),
            ("protection_continuous_through_merge", False), ("approved_at", MERGED),
        ):
            with self.subTest(field=field):
                self.receipt = original | {field: replacement}
                self.enroll_fixture_receipt()
                self.assert_rejected("The receipt must show" if field != "protection_continuous_through_merge"
                                     else "does not bind this exact integration")
        self.check_current_protection.assert_not_called()

    def test_required_source_update_cannot_be_proved_by_ancestry_or_current_policy(self):
        original = deepcopy(self.github_responses)
        for path, field, replacement, message in (
            (f"{API}/pulls/{PR}", "merged_by", {"id": 12000, "type": "User"}, "owner-merged"),
            (f"{API}/pulls/{PR}", "merge_commit_sha", HEAD, "owner-merged"),
            (f"{API}/git/commits/{SOURCE}", "parents", [{"sha": CONFIGURATION}, {"sha": HEAD}], "two parents"),
            (f"{API}/compare/{SOURCE}...{CURRENT_MAIN}?per_page=1", "status", "diverged", "remains on main"),
            (PR_JOBS, "total_count", 21, "incomplete list of jobs"),
            (RUN_PATH, "created_at", APPROVED, "predates reviewed integration"),
        ):
            with self.subTest(field=field):
                self.github_responses = deepcopy(original)
                self.github_responses[path][field] = replacement
                self.assert_rejected(message)

    def test_pr_checks_must_match_current_approved_attempt_and_publisher(self):
        changes = (
            (NATIVE_PATH, "run_attempt", 2, "no longer the run's current attempt"),
            (f"{API}/check-runs/301", "app", {"id": 5}, "published by the GitHub Actions app"),
            (f"{API}/check-runs/301", "conclusion", "neutral", "published by the GitHub Actions app"),
        )
        original = deepcopy(self.github_responses)
        for path, field, replacement, message in changes:
            with self.subTest(field=field):
                self.github_responses = deepcopy(original)
                self.github_responses[path][field] = replacement
                self.assert_rejected(message)
        self.github_responses = deepcopy(original)
        self.github_responses[PR_JOBS]["jobs"][0]["completed_at"] = BUILD_COMPLETE
        self.assert_rejected("approval predates the successful native PR checks")
        self.github_responses = deepcopy(original)
        self.github_responses[NATIVE_PATH]["pull_requests"] = [{"number": PR + 1}]
        self.assert_rejected("PR association conflicts with the owner receipt")

    def test_failed_incomplete_or_partially_rerun_workflow_is_rejected(self):
        run = self.github_responses[RUN_PATH]
        for status, conclusion in (("completed", "failure"), ("completed", "neutral"), ("in_progress", None)):
            with self.subTest(status=status, conclusion=conclusion):
                self.github_responses[RUN_PATH] = run | {"status": status, "conclusion": conclusion}
                self.assert_rejected("attempt must finish successfully")
        self.github_responses[RUN_PATH] = run
        job = self.github_responses[JOBS]["jobs"][-1]
        for field, value in (("conclusion", "skipped"), ("conclusion", "neutral"), ("run_attempt", ATTEMPT - 1)):
            with self.subTest(field=field, value=value):
                original = job[field]
                job[field] = value
                self.assert_rejected("Publish (arm64) must succeed in the selected attempt")
                job[field] = original

    def test_release_or_pr_rerun_during_verification_fails_closed(self):
        for path, message in ((RUN_PATH, "main workflow attempt changed"), (NATIVE_PATH, "PR check attempt changed")):
            with self.subTest(path=path):
                self.attempt_reads.clear()
                self.rerun = path
                self.assert_rejected(message)

    def test_current_artifact_must_match_attempt_revision_and_platform(self):
        provenance = self.provenance["arm64"].copy()
        for field, value in (
            ("run_attempt", "1"), ("revision", HEAD), ("architecture", "amd64"),
            ("run_url", f"{WEB}/actions/runs/{NATIVE_RUN_ID}"),
        ):
            with self.subTest(field=field):
                self.provenance["arm64"] = provenance | {field: value}
                self.build_archive("arm64")
                self.assert_rejected("provenance does not match the exact run, attempt, platform and revision")

    def test_expired_unbound_stale_or_corrupted_archive_is_rejected(self):
        for field, value, message in (
            ("expired", True, "one current amd64 provenance artifact"),
            ("created_at", APPROVED, "was not uploaded during its publication job"),
            ("workflow_run", {"id": NATIVE_RUN_ID}, "one current amd64 provenance artifact"),
            ("digest", verifier.digest(b"wrong"), "archive differs from GitHub's digest"),
        ):
            with self.subTest(field=field):
                self.build_archive("amd64")
                self.artifact("amd64")[field] = value
                self.assert_rejected(message)
        self.build_archive("amd64", extra_file=True)
        self.assert_rejected("provenance archive has unexpected contents")
        self.build_archive("amd64", compression=ZIP_BZIP2)
        self.assert_rejected("provenance archive has unexpected contents")

    def test_mixed_image_references_are_rejected(self):
        provenance = self.provenance["arm64"]
        runtime = provenance["images"]["runtime"]
        bad_images = (
            ("runtime", f"ghcr.io/{verifier.REPOSITORY}-runtime:latest", "immutable GHCR digest"),
            ("migration", runtime, "expected migration repository"),
            ("runtime", self.provenance["amd64"]["images"]["runtime"], "platform does not match linux/arm64"),
        )
        images = provenance["images"].copy()
        for role, reference, message in bad_images:
            with self.subTest(role=role, reference=reference):
                provenance["images"] = images | {role: reference}
                self.build_archive("arm64")
                self.assert_rejected(message)

    def test_registry_digest_platform_and_source_mismatch_fail_closed(self):
        reference = self.provenance["amd64"]["images"]["migration"]
        image = self.images[reference]
        manifest = self.manifests[reference]
        self.manifests[reference] = b"other bytes"
        self.assert_rejected("manifest does not match its immutable digest")
        self.manifests[reference] = manifest
        self.images[reference] = image | {"os": "windows"}
        self.assert_rejected("image platform does not match linux/amd64")
        self.images[reference] = deepcopy(image)
        self.images[reference]["config"]["Labels"]["org.opencontainers.image.revision"] = HEAD
        self.assert_rejected("source or revision label differs")
        self.images[reference] = deepcopy(image)
        self.images[reference]["config"]["Labels"]["org.opencontainers.image.source"] = "https://github.invalid"
        self.assert_rejected("source or revision label differs")

    def test_unknown_provider_or_registry_results_do_not_leak_raw_diagnostics(self):
        failure = subprocess.CalledProcessError(1, ["upstream"], stderr=SECRET.encode())
        run = self.github_responses[RUN_PATH]
        self.github_responses[RUN_PATH] = failure
        self.assert_rejected("GitHub evidence is unavailable")
        self.github_responses[RUN_PATH] = {"unexpected_secret": SECRET}
        self.assert_rejected("wrong repository")
        self.github_responses[RUN_PATH] = run
        reference = self.provenance["amd64"]["images"]["runtime"]
        manifest = self.manifests[reference]
        self.manifests[reference] = subprocess.TimeoutExpired(["docker"], 25, stderr=SECRET.encode())
        self.assert_rejected("GHCR amd64 runtime evidence is unavailable")
        self.manifests[reference] = manifest
        self.check_current_protection.side_effect = failure
        self.assert_rejected("Main protection readback failed")

    def test_invalid_cli_arguments_do_not_echo_user_data(self):
        stderr = StringIO()
        with self.assertRaises(SystemExit) as failure, redirect_stderr(stderr):
            verifier.main(["--run-id", SECRET])
        self.assertEqual(failure.exception.code, 2)
        self.assertNotIn(SECRET, stderr.getvalue())
