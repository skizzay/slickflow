"""Exercise publication event gates and failure behavior without registry access."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = 'skizzay/slickflow'
MAIN = 'refs/heads/main'
TRUSTED_SOURCES = [('push', MAIN, REPOSITORY), ('workflow_dispatch', MAIN, REPOSITORY)]
FORBIDDEN_SOURCES = [
    ('pull_request', 'refs/pull/1/merge', REPOSITORY),
    ('pull_request', MAIN, REPOSITORY),
    ('pull_request_target', MAIN, REPOSITORY),
    ('push', 'refs/heads/epic/108', REPOSITORY),
    ('push', 'refs/heads/epic/128', REPOSITORY),
    ('workflow_dispatch', 'refs/heads/epic/128', REPOSITORY),
    ('push', 'refs/heads/feature/128-135', REPOSITORY),
    ('workflow_dispatch', 'refs/heads/feature/128-135', REPOSITORY),
    ('push', 'refs/tags/main', REPOSITORY),
    ('workflow_dispatch', 'refs/tags/main', REPOSITORY),
    ('workflow_dispatch', 'refs/heads/Main', REPOSITORY),
    ('push', MAIN, 'someone-else/slickflow'),
    ('workflow_dispatch', MAIN, 'Skizzay/slickflow'),
    ('schedule', MAIN, REPOSITORY),
    ('', '', REPOSITORY),
]


class PublicationWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.header, _, jobs = (ROOT / '.github/workflows/control-plane.yaml').read_text().partition('\njobs:\n')
        _, *parts = re.split(r'^  ([a-z][a-z-]+):\n', jobs, flags=re.MULTILINE)
        self.jobs = dict(zip(parts[::2], parts[1::2]))

    def test_pull_requests_use_both_native_checks_with_read_only_permissions(self):
        self.assertRegex(self.header, r"(?m)^  pull_request:\n    branches: \[main, 'epic/\*'\]$")
        self.assertRegex(self.header, r'(?m)^  push:\n    branches: \[main\]$')
        self.assertNotIn('pull_request_target', self.header)
        self.assertRegex(self.header, r'(?m)^permissions:\n  contents: read\n\n')
        verify = self.jobs['verify']
        self.assertIn('    name: Verify (${{ matrix.arch }})\n', verify)
        self.assertIn('          - arch: amd64\n            runner: ubuntu-24.04\n', verify)
        self.assertIn('          - arch: arm64\n            runner: ubuntu-24.04-arm\n', verify)
        self.assertIn('    runs-on: ${{ matrix.runner }}\n', verify)
        self.assertIn('          persist-credentials: false\n', verify)
        for name, job in self.jobs.items():
            if name != 'publish':
                self.assertNotRegex(job, r': write\b|write-all\b|secrets\s*[.\[]|docker login')

    def test_only_publication_job_can_authenticate_after_both_native_checks_and_source_guard(self):
        publish = self.jobs['publish']
        self.assertIn('    needs: [verify, publication-source]\n', publish)
        self.assertIn("    if: needs.publication-source.outputs.allowed == 'true'\n", publish)
        self.assertRegex(publish, r'(?m)^    permissions:\n      contents: read\n      packages: write\n    strategy:')
        self.assertIn('          ref: ${{ github.sha }}\n          persist-credentials: false\n', publish)
        self.assertLess(publish.index('run: ./scripts/publish-control-plane.sh --check-source'),
                        publish.index('GHCR_TOKEN: ${{ secrets.GITHUB_TOKEN }}'))

    def test_read_only_job_computes_exact_source_eligibility(self):
        source = self.jobs['publication-source']
        self.assertIn('    permissions: {}\n', source)
        self.assertIn('      allowed: ${{ steps.source.outputs.allowed }}\n', source)
        match = re.search(r'^        id: source\n        shell: bash\n        run: \|\n((?: {10}[^\n]*\n)+)',
                          source, re.MULTILINE)
        self.assertIsNotNone(match)
        body = textwrap.dedent(match.group(1))
        for cases, allowed in [(TRUSTED_SOURCES, 'true'), (FORBIDDEN_SOURCES, 'false')]:
            for event, ref, repository in cases:
                with self.subTest(event=event, ref=ref, repository=repository), tempfile.TemporaryDirectory() as folder:
                    output = Path(folder) / 'output'
                    env = {'GITHUB_EVENT_NAME': event, 'GITHUB_REF': ref,
                           'GITHUB_REPOSITORY': repository, 'GITHUB_OUTPUT': str(output)}
                    subprocess.run(['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c', body],
                                   env=env, check=True)
                    self.assertEqual(output.read_text(), f'allowed={allowed}\n')


class PublicationTest(unittest.TestCase):
    def run_publication(self, event='push', ref=MAIN, repository=REPOSITORY, *, fail='', summary=True,
                        arch='amd64', sha=None, check_source=False):
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
    else: print(os.environ['SLICKFLOW_PUBLISH_ARCH'] + ' 10001:10001')
''')
            docker.chmod(0o755)
            env = dict(os.environ, PATH=folder + os.pathsep + os.environ['PATH'],
                       GITHUB_REPOSITORY=repository, GITHUB_SHA=sha or revision,
                       GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='2', GITHUB_STEP_SUMMARY=str(work / 'summary'),
                       GITHUB_EVENT_NAME=event, GITHUB_REF=ref,
                       SLICKFLOW_PUBLISH_ARCH=arch, CALL_LOG=str(work / 'calls'), FAIL_PUSH=fail)
            if not summary:
                env.pop('GITHUB_STEP_SUMMARY', None)
            command = ['bash', str(work / 'scripts/publish-control-plane.sh')]
            if check_source:
                command.append('--check-source')
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            calls = (work / 'calls').read_text() if (work / 'calls').exists() else ''
            manifest = work / f'provenance-{arch}.json'
            return result, calls, json.loads(manifest.read_text()) if manifest.exists() else None

    def test_untrusted_source_cannot_publish(self):
        for event, ref, repository in FORBIDDEN_SOURCES:
            with self.subTest(event=event, ref=ref, repository=repository):
                result, calls, manifest = self.run_publication(event, ref, repository)
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

    def test_pre_authentication_check_requires_trusted_source_and_matching_checkout(self):
        result, calls, manifest = self.run_publication(check_source=True, summary=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, '')
        self.assertIsNone(manifest)
        for inputs, message in [({'sha': 'a' * 40}, 'checkout does not match'),
                                ({'ref': 'refs/heads/epic/128'}, 'on refs/heads/main')]:
            with self.subTest(inputs=inputs):
                result, calls, manifest = self.run_publication(check_source=True, **inputs)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(calls, '')
                self.assertIsNone(manifest)

    def test_push_failure_cannot_report_success_or_pair(self):
        result, calls, manifest = self.run_publication(fail='yes')
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(manifest)
        self.assertEqual(sum(json.loads(line)[0] == 'push' for line in calls.splitlines()), 1)

    def test_trusted_success_records_both_digests_and_pipeline(self):
        for event, ref, repository in TRUSTED_SOURCES:
            for arch in ['amd64', 'arm64']:
                with self.subTest(event=event, arch=arch):
                    result, calls, manifest = self.run_publication(event, ref, repository, arch=arch)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(manifest['images'], {
                        target: f'ghcr.io/{repository}-{target}@sha256:' + 'a' * 64
                        for target in ['runtime', 'migration']
                    })
                    self.assertEqual(manifest['run_url'], 'https://github.com/skizzay/slickflow/actions/runs/123')
                    self.assertEqual(manifest['run_attempt'], '2')
                    self.assertEqual(manifest['architecture'], arch)
                    self.assertRegex(manifest['revision'], r'^[a-f0-9]{40}$')
                    self.assertIn(f'{manifest["revision"]}-{arch}', calls)


if __name__ == '__main__':
    unittest.main()
