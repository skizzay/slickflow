"""Exercise publication event gates and failure behavior without registry access."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = 'skizzay/slickflow'
BINDING = 'forgejo.private.invalid/synthetic-namespace'
PIN = 'sha256:' + hashlib.sha256(BINDING.encode()).hexdigest()
TOKEN = 'synthetic-forgejo-token'
USERNAME = 'synthetic-publisher'
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
                self.assertNotRegex(job, r': write\b|write-all\b|secrets\s*[.\[]|docker login|SLICKFLOW_REGISTRY_')
                self.assertNotIn('control-plane-publication', job)

    def test_only_publication_job_can_authenticate_after_both_native_checks_and_source_guard(self):
        publish = self.jobs['publish']
        self.assertIn('    needs: [verify, publication-source]\n', publish)
        self.assertIn("    if: needs.publication-source.outputs.allowed == 'true'\n", publish)
        self.assertIn('    environment: control-plane-publication\n', publish)
        self.assertRegex(publish, r'(?m)^    permissions:\n      contents: read\n    strategy:')
        self.assertIn('          ref: ${{ github.sha }}\n          persist-credentials: false\n', publish)
        self.assertNotRegex(publish, r'packages: write|secrets\.|ghcr\.io')
        handoff = publish.index('SLICKFLOW_REGISTRY_AUTH_FILE:')
        self.assertLess(publish.index('run: ./scripts/publish-control-plane.sh --check-source'), handoff)
        self.assertLess(publish.index('./scripts/verify-hosting.sh --webhooks'), handoff)
        self.assertIn('      - name: Remove publication handoff\n        if: always()', publish)

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
                        arch='amd64', sha=None, check_source=False, auth='file', pin=PIN, credentials=None):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / 'scripts').mkdir()
            for name in ('publish-control-plane.sh', 'publish_control_plane.py', 'control_plane_registry.py'):
                shutil.copyfile(ROOT / 'scripts' / name, work / 'scripts' / name)
            # A separate tiny Git fixture keeps provenance and test files out of the checkout.
            subprocess.run(['git', 'init', '-q', folder], check=True)
            subprocess.run(['git', '-C', folder, '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit',
                            '--no-gpg-sign', '--allow-empty', '-qm', 'synthetic'], check=True)
            revision = subprocess.check_output(['git', '-C', folder, 'rev-parse', 'HEAD'], text=True).strip()
            docker = work / 'docker'
            docker.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
config = None
if args[:1] == ['--config']:
    config = args[1]
    args = args[2:]
with open(os.environ['CALL_LOG'], 'a') as log:
    log.write(json.dumps({'args': args, 'config': config}) + '\\n')
if args[0] == 'login':
    assert config, 'expected an isolated config'
    entry = json.loads((pathlib.Path(config) / 'config.json').read_text())
    assert entry == {'auths': {args[-1]: {}}}, 'unexpected auth destinations'
    assert sys.stdin.read() == os.environ['FAKE_TOKEN'] + '\\n'
    if os.environ['FAIL'] == 'login':
        print(args[-1], os.environ['FAKE_TOKEN'], file=sys.stderr)
        sys.exit(1)
if args[0] == 'push':
    print(args[1], os.environ['FAKE_TOKEN'])
    if os.environ['FAIL'] and os.environ['FAIL'] in args[1]:
        print(args[1], os.environ['FAKE_TOKEN'], file=sys.stderr)
        sys.exit(1)
if args[:2] == ['image', 'inspect']:
    fmt = args[-1]
    if 'RepoDigests' in fmt:
        repo = args[2].split(':')[0]
        if os.environ['FAIL'] == 'digest':
            repo = 'unapproved.invalid/other/slickflow-runtime'
        digest = 'a' if 'runtime' in repo else 'b'
        print(json.dumps([repo + '@sha256:' + digest * 64]))
    else:
        commit = os.environ['GITHUB_SHA']
        arch = os.environ['SLICKFLOW_PUBLISH_ARCH']
        print(f'{commit} linux/{arch} 10001:10001')
''')
            docker.chmod(0o755)
            auth_file = work / 'handoff'
            if auth != 'missing':
                auth_file.write_text(json.dumps(credentials if credentials is not None else
                    {'registry': BINDING, 'registry_binding_sha256': PIN, 'username': USERNAME, 'token': TOKEN}))
                auth_file.chmod(0o644 if auth == 'public' else 0o600)
            if auth == 'symlink':
                link = work / 'alias'
                link.symlink_to(auth_file)
                auth_file = link
            env = dict(os.environ, PATH=folder + os.pathsep + os.environ['PATH'],
                       GITHUB_REPOSITORY=repository, GITHUB_SHA=sha or revision,
                       GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='2', GITHUB_STEP_SUMMARY=str(work / 'summary'),
                       GITHUB_EVENT_NAME=event, GITHUB_REF=ref, SLICKFLOW_REGISTRY_AUTH_FILE=str(auth_file),
                       SLICKFLOW_REGISTRY_BINDING_SHA256=pin,
                       SLICKFLOW_PUBLISH_ARCH=arch, CALL_LOG=str(work / 'calls'), FAIL=fail, FAKE_TOKEN=TOKEN)
            if auth == 'relative':
                env['SLICKFLOW_REGISTRY_AUTH_FILE'] = auth_file.name
            if not summary:
                env.pop('GITHUB_STEP_SUMMARY', None)
            command = ['bash', str(work / 'scripts/publish-control-plane.sh')]
            if check_source:
                command.append('--check-source')
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            calls = (work / 'calls').read_text() if (work / 'calls').exists() else ''
            self.calls = [json.loads(line) for line in calls.splitlines()]
            self.summary = (work / 'summary').read_text() if (work / 'summary').exists() else ''
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
        self.assertIn('pipeline summary path is required', result.stderr)
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

    def assert_private_output(self, result):
        output = result.stdout + result.stderr + self.summary
        for value in (BINDING, BINDING.split('/')[0], BINDING.split('/')[1], TOKEN, USERNAME):
            self.assertNotIn(value, output)

    def test_partial_push_failure_cannot_report_success_or_pair(self):
        result, _, manifest = self.run_publication(fail='slickflow-migration')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('did not confirm', result.stderr)
        self.assertIsNone(manifest)
        self.assertEqual(sum(call['args'][0] == 'push' for call in self.calls), 2)
        self.assertEqual(self.summary, '')
        self.assert_private_output(result)
        configs = {call['config'] for call in self.calls if call['config']}
        self.assertEqual(len(configs), 1)
        self.assertFalse(Path(configs.pop()).exists())

    def test_login_and_digest_failures_are_redacted_without_a_pair(self):
        for fail, message in [('login', 'authentication failed'), ('digest', 'one immutable digest')]:
            with self.subTest(fail=fail):
                result, _, manifest = self.run_publication(fail=fail)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertIsNone(manifest)
                self.assert_private_output(result)

    def test_missing_insecure_or_unapproved_handoff_cannot_route_credentials(self):
        base_credentials = {'registry': BINDING, 'registry_binding_sha256': PIN,
                            'username': USERNAME, 'token': TOKEN}
        other = 'unexpected.private.invalid/other'
        other_pin = 'sha256:' + hashlib.sha256(other.encode()).hexdigest()
        cases = [
            *({'auth': auth} for auth in ('missing', 'public', 'symlink', 'relative')),
            {'pin': ''},
            {'credentials': base_credentials | {'registry_binding_sha256': other_pin}},
            {'credentials': base_credentials | {'registry': other, 'registry_binding_sha256': other_pin}},
            {'credentials': base_credentials | {'registry': 'ghcr.io/skizzay'}},
            {'credentials': base_credentials | {'token': TOKEN + '\n'}},
        ]
        for options in cases:
            with self.subTest(case=options.keys()):
                result, _, manifest = self.run_publication(**options)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(manifest)
                self.assertEqual([call['args'][:2] for call in self.calls], [['image', 'inspect']] * 2)
                self.assert_private_output(result)
                self.assertNotIn(other, result.stderr)

    def test_trusted_success_records_both_digests_and_pipeline(self):
        for event, ref, repository in TRUSTED_SOURCES:
            for arch in ['amd64', 'arm64']:
                with self.subTest(event=event, arch=arch):
                    result, calls, manifest = self.run_publication(event, ref, repository, arch=arch)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(manifest['images'], {'runtime': 'sha256:' + 'a' * 64,
                                                          'migration': 'sha256:' + 'b' * 64})
                    self.assertEqual(manifest['registry_binding_sha256'], PIN)
                    self.assertEqual(manifest['run_url'], 'https://github.com/skizzay/slickflow/actions/runs/123')
                    self.assertEqual(manifest['run_attempt'], '2')
                    self.assertEqual(manifest['architecture'], arch)
                    self.assertRegex(manifest['revision'], r'^[a-f0-9]{40}$')
                    self.assertIn(f'{manifest["revision"]}-{arch}', calls)
                    tag = f'{manifest["revision"]}-{arch}'
                    self.assertEqual([call['args'] for call in self.calls if call['args'][0] == 'push'],
                                     [['push', f'{BINDING}/slickflow-{role}:{tag}'] for role in ('runtime', 'migration')])
                    login, = [call for call in self.calls if call['args'][0] == 'login']
                    self.assertEqual(login['args'], ['login', '--username', USERNAME, '--password-stdin',
                                                     BINDING.split('/')[0]])
                    self.assertFalse(Path(login['config']).exists())
                    self.assertNotIn(TOKEN, calls)
                    self.assert_private_output(result)
                    self.assertIn(PIN, self.summary)


if __name__ == '__main__':
    unittest.main()
