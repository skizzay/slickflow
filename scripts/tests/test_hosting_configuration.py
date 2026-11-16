"""Host separation checks using real Docker Compose interpolation, without services."""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HostingConfigurationTest(unittest.TestCase):
    def config(self, role):
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
        recipe = 'compose.yaml' if role == 'runtime' else 'compose.migration.yaml'
        result = subprocess.run(
            ['docker', 'compose', '-p', 'slickflow-test', '-f',
             str(ROOT / 'deployment/control-plane' / recipe), 'config', '--format', 'json'],
            env=env, text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_runtime_needs_only_runtime_inputs_and_stays_loopback(self):
        config = self.config('runtime')
        self.assertEqual(set(config['services']), {'runtime'})
        self.assertEqual(set(config['secrets']), {'runtime_password'})
        service = config['services']['runtime']
        self.assertEqual(service['ports'][0]['host_ip'], '127.0.0.1')
        self.assertNotIn('network_mode', service)
        self.assertEqual(service['environment']['SLICKFLOW_DB_USER'], 'slickflow_runtime')
        self.assertIn('--slickflow.execution.enabled=false', service['command'])

    def test_migration_preserves_approved_source_without_runtime_secret(self):
        config = self.config('migration')
        self.assertEqual(set(config['services']), {'migration'})
        self.assertEqual(set(config['secrets']), {'migration_password'})
        service = config['services']['migration']
        self.assertEqual(service['network_mode'], 'host')
        self.assertEqual(service['environment']['SLICKFLOW_DB_RUNTIME_ROLE'], 'slickflow_runtime')
        self.assertNotIn('ports', service)
        self.assertTrue(service['read_only'])
        self.assertEqual(service['restart'], 'no')

    def test_preflight_rejects_mutable_images_for_each_role(self):
        for role in ('runtime', 'migration'):
            with self.subTest(role=role):
                env = dict(os.environ)
                env['SLICKFLOW_' + role.upper() + '_IMAGE'] = 'example/image:latest'
                result = subprocess.run(
                    ['bash', str(ROOT / 'scripts/check-control-plane-host.sh'), role],
                    env=env, text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('must be an immutable image', result.stderr)


if __name__ == '__main__':
    unittest.main()
