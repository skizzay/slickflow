"""Exercise publication event gates and failure behavior without registry access."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PublicationTest(unittest.TestCase):
    def run_publication(self, event='push', ref='refs/heads/epic/108', fail='', summary=True, repository='skizzay/slickflow',
                        arch='amd64', sha=None):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / 'scripts').mkdir()
            (work / 'scripts/publish-control-plane.sh').write_bytes(
                (ROOT / 'scripts/publish-control-plane.sh').read_bytes())
            # A separate tiny Git fixture keeps provenance and test files out of the checkout.
            subprocess.run(['git', 'init', '-q', folder], check=True)
            subprocess.run(['git', '-C', folder, '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit',
                            '--no-gpg-sign', '--allow-empty', '-qm', 'synthetic'], check=True)
            revision = subprocess.check_output(['git', '-C', folder, 'rev-parse', 'HEAD'], text=True).strip()
            docker = work / 'docker'
            docker.write_text('''#!/usr/bin/env python3
import json,os,pathlib,sys
args=sys.argv[1:]
with open(os.environ['CALL_LOG'],'a') as log: log.write(json.dumps(args)+'\\n')
if args[0]=='push' and os.environ.get('FAIL_PUSH'): sys.exit(1)
if args[:2]==['image','inspect']:
    fmt=args[-1]
    if 'revision' in fmt: print(os.environ['GITHUB_SHA'])
    elif 'RepoDigests' in fmt: print(json.dumps([args[2].split(':')[0]+'@sha256:'+'a'*64]))
    else: print('amd64 10001:10001')
''')
            docker.chmod(0o755)
            env = dict(os.environ, PATH=folder + os.pathsep + os.environ['PATH'],
                       GITHUB_REPOSITORY=repository, GITHUB_SHA=sha or revision,
                       GITHUB_RUN_ID='123', GITHUB_STEP_SUMMARY=str(work / 'summary'),
                       GITHUB_EVENT_NAME=event, GITHUB_REF=ref,
                       SLICKFLOW_PUBLISH_ARCH=arch, CALL_LOG=str(work / 'calls'), FAIL_PUSH=fail)
            if not summary:
                env.pop('GITHUB_STEP_SUMMARY', None)
            result = subprocess.run(['bash', str(work / 'scripts/publish-control-plane.sh')],
                                    env=env, capture_output=True, text=True)
            calls = (work / 'calls').read_text() if (work / 'calls').exists() else ''
            manifest = work / 'provenance-amd64.json'
            return result, calls, json.loads(manifest.read_text()) if manifest.exists() else None

    def test_pr_and_unapproved_branches_cannot_publish(self):
        for event, ref in [('pull_request', 'refs/pull/1/merge'),
                           ('push', 'refs/heads/feature/108-112'),
                           ('workflow_dispatch', 'refs/heads/feature/108-112')]:
            with self.subTest(event=event, ref=ref):
                result, calls, manifest = self.run_publication(event, ref)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, '')
                self.assertIsNone(manifest)

    def test_invalid_identity_or_architecture_has_clear_prepublication_error(self):
        for inputs, message in [
            ({'repository': 'other/repo'}, 'requires skizzay/slickflow'),
            ({'sha': 'invalid'}, 'full lowercase commit SHA'),
            ({'sha': 'a' * 40}, 'checkout does not match'),
            ({'arch': 'ppc64le'}, 'only native amd64 or arm64'),
        ]:
            with self.subTest(inputs=inputs):
                result, calls, manifest = self.run_publication(**inputs)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(calls, '')
                self.assertIsNone(manifest)

    def test_missing_summary_fails_before_publication(self):
        result, calls, manifest = self.run_publication(summary=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('pipeline summary path required', result.stderr)
        self.assertEqual(calls, '')
        self.assertIsNone(manifest)

    def test_push_failure_cannot_report_success_or_pair(self):
        result, calls, manifest = self.run_publication(fail='yes')
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(manifest)
        self.assertEqual(sum(json.loads(line)[0] == 'push' for line in calls.splitlines()), 1)

    def test_trusted_success_records_both_digests_and_pipeline(self):
        result, calls, manifest = self.run_publication()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(manifest['images']), {'runtime', 'migration'})
        self.assertTrue(all('@sha256:' in image for image in manifest['images'].values()))
        self.assertEqual(manifest['run_url'], 'https://github.com/skizzay/slickflow/actions/runs/123')
        self.assertEqual(manifest['architecture'], 'amd64')


if __name__ == '__main__':
    unittest.main()
