"""Host separation checks using real Docker Compose interpolation, without services."""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HostingConfigurationTest(unittest.TestCase):
    def config(self, role, webhooks=False, signing_secret=True):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('SLICKFLOW_')}
        env.update({
            'SLICKFLOW_' + role.upper() + '_IMAGE': 'example/image@sha256:' + 'a' * 64,
            'SLICKFLOW_' + role.upper() + '_PASSWORD_FILE': '/synthetic/' + role,
            'SLICKFLOW_DB_URL': 'jdbc:postgresql://db.invalid/slickflow?currentSchema=slickflow&sslmode=verify-full&sslrootcert=/run/trust/postgresql-ca.crt',
            'SLICKFLOW_DB_CA_FILE': '/synthetic/ca.crt',
            'SLICKFLOW_CPU_LIMIT': '1',
        })
        if role == 'migration':
            env['SLICKFLOW_MIGRATION_MEMORY'] = '1g'
        if signing_secret:
            env['SLICKFLOW_WEBHOOK_SECRET_FILE'] = '/synthetic/signing-secret'
        recipe = 'compose.yaml' if role == 'runtime' else 'compose.migration.yaml'
        args = ['docker', 'compose', '-p', 'slickflow-test', '-f',
                str(ROOT / 'deployment/control-plane' / recipe)]
        if webhooks:
            args += ['-f', str(ROOT / 'deployment/control-plane/compose.webhook.yaml')]
        result = subprocess.run(
            args + ['config', '--format', 'json'],
            env=env, text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_runtime_needs_only_runtime_inputs_and_stays_loopback(self):
        config = self.config('runtime')
        self.assertEqual(set(config['services']), {'runtime'})
        self.assertEqual(set(config['secrets']), {'runtime_password'})
        service = config['services']['runtime']
        self.assertEqual(service['tmpfs'], ['/tmp:size=64m,mode=1777'])
        self.assertEqual(service['ports'][0]['host_ip'], '127.0.0.1')
        self.assertNotIn('network_mode', service)
        self.assertEqual(service['environment']['SLICKFLOW_DB_USER'], 'slickflow_runtime')
        self.assertIn('--slickflow.execution.enabled=false', service['command'])

    def test_receipt_overlay_preserves_containment_and_separates_secrets(self):
        config = self.config('runtime', webhooks=True)
        self.assertEqual(set(config['services']), {'runtime'})
        self.assertEqual(set(config['secrets']), {'runtime_password', 'webhook_signing_secret'})
        service = config['services']['runtime']
        self.assertEqual(service['ports'][0]['host_ip'], '127.0.0.1')
        self.assertEqual(service['command'], [
            '--slickflow.execution.enabled=false',
            '--slickflow.execution.inbox.enabled=false',
            '--slickflow.manual-approval.enabled=false',
            '--slickflow.worker.enabled=false',
            '--slickflow.github.webhook.enabled=true'])
        self.assertEqual(service['environment']['SLICKFLOW_GITHUB_WEBHOOK_ENABLED'], 'true')
        self.assertEqual({secret['target'] for secret in service['secrets']},
                         {'SLICKFLOW_DB_PASSWORD', 'SLICKFLOW_GITHUB_WEBHOOK_SECRET'})
        self.assertTrue(service['read_only'])
        base = self.config('runtime')['services']['runtime']
        self.assertIn('--slickflow.github.webhook.enabled=false', base['command'])
        for key in ('image', 'volumes', 'mem_limit', 'cpus', 'tmpfs', 'cap_drop', 'security_opt'):
            self.assertEqual(service[key], base[key], key)

    def test_receipt_overlay_requires_separate_signing_secret(self):
        with self.assertRaises(subprocess.CalledProcessError) as result:
            self.config('runtime', webhooks=True, signing_secret=False)
        self.assertIn('external webhook signing secret required', result.exception.stderr)

    def test_migration_preserves_approved_source_without_runtime_secret(self):
        config = self.config('migration')
        self.assertEqual(set(config['services']), {'migration'})
        self.assertEqual(set(config['secrets']), {'migration_password'})
        service = config['services']['migration']
        self.assertEqual(service['tmpfs'], ['/tmp:size=64m,mode=1777'])
        self.assertEqual(service['network_mode'], 'host')
        self.assertEqual(service['environment']['SLICKFLOW_DB_RUNTIME_ROLE'], 'slickflow_runtime')
        self.assertNotIn('ports', service)
        self.assertTrue(service['read_only'])
        self.assertEqual(service['restart'], 'no')

    def test_preflight_rejects_mutable_images_for_each_role(self):
        for role in ('runtime', 'migration', 'runtime-webhook'):
            with self.subTest(role=role):
                env = dict(os.environ)
                env['SLICKFLOW_' + role.split('-')[0].upper() + '_IMAGE'] = 'example/image:latest'
                result = subprocess.run(
                    ['bash', str(ROOT / 'scripts/check-control-plane-host.sh'), role],
                    env=env, text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('must be an immutable image', result.stderr)


if __name__ == '__main__':
    unittest.main()
