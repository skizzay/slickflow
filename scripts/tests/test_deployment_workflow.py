"""Exercise dispatch input handling without invoking any installed launcher."""
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/deploy-control-plane.yaml'


class DeploymentWorkflowTest(unittest.TestCase):
    def invoke(self, action, release=''):
        body = textwrap.dedent(WORKFLOW.read_text().split('        run: |\n', 1)[1])
        # Override the Bash builtin so tests capture the fixed invocation only.
        harness = 'exec() { printf "%s\\n" "$@"; }\n' + body
        return subprocess.run(['bash', '-c', harness], capture_output=True, text=True,
                              env=dict(os.environ, ACTION=action, RELEASE_ID=release))

    def test_probe_preserves_existing_fixed_command(self):
        result = self.invoke('probe')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['/usr/local/bin/slickflow-deploy', 'probe'])

    def test_deploy_accepts_only_opaque_release_identifier(self):
        release = 'a1' * 16
        result = self.invoke('deploy', release)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ['/usr/local/bin/slickflow-deploy', 'deploy', '--release', release])

    def test_probe_rejects_release_and_unknown_action_cannot_invoke_launcher(self):
        for action, release in [('probe', 'a' * 32), ('delete', ''), ('', '')]:
            with self.subTest(action=action):
                result = self.invoke(action, release)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('/usr/local/bin/slickflow-deploy', result.stdout)

    def test_deploy_rejects_missing_malformed_or_shell_input(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'must-not-exist'
            values = ['', 'a' * 31, 'a' * 33, 'A' * 32, '../release',
                      'a' * 32 + '\n', f'$(touch {marker})', f'; touch {marker}']
            for release in values:
                with self.subTest(release=release):
                    result = self.invoke('deploy', release)
                    self.assertEqual(result.returncode, 2)
                    self.assertNotIn('/usr/local/bin/slickflow-deploy', result.stdout)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
