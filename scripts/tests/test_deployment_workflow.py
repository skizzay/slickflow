"""Exercise dispatch input handling without invoking any installed launcher."""
import os
import re
import shlex
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/deploy-control-plane.yaml'


def workflow_script(source):
    source = source.replace('\r\n', '\n').replace('\r', '\n')
    lines = source.splitlines(keepends=True)
    markers = [i for i, line in enumerate(lines)
               if re.fullmatch(r' *run:\s*\|[-+]?[ \t]*(?:#.*)?', line.rstrip('\r\n'))]
    if len(markers) != 1:
        raise ValueError('Expected one literal launcher script in this workflow')
    start = markers[0]
    indentation = len(lines[start]) - len(lines[start].lstrip(' '))
    block = []
    for line in lines[start + 1:]:
        if line.strip() and len(line) - len(line.lstrip(' ')) <= indentation:
            break
        block.append(line)
    if not any(line.strip() for line in block):
        raise ValueError('Launcher script is empty')
    return textwrap.dedent(''.join(block))


class DeploymentWorkflowTest(unittest.TestCase):
    def invoke(self, action, release='', startup_env=None):
        source = WORKFLOW.read_text()
        body = workflow_script(source)
        shells = re.findall(r'^ +shell: *(.+?) *$', source, re.MULTILINE)
        self.assertEqual(len(shells), 1)
        shell = shlex.split(shells[0])
        if shell == ['bash']:
            shell += ['--noprofile', '--norc', '-e', '-o', 'pipefail', '{0}']
        self.assertEqual(shell.count('{0}'), 1)
        # Capture the fixed invocation without invoking an installed launcher.
        # Also verify startup-hook variables are absent from the running shell.
        harness = ('[[ ! ${BASH_ENV+x} && ! ${ENV+x} ]] || exit 98\n'
                   'exec() { printf "%s\\n" "$@"; }\n' + body)
        env = {'PATH': os.defpath, 'LANG': 'C', 'ACTION': action, 'RELEASE_ID': release}
        env.update(startup_env or {})
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'dispatch.sh'
            script.write_text(harness)
            return subprocess.run([str(script) if part == '{0}' else part for part in shell],
                                  capture_output=True, text=True, env=env)

    def test_workflow_shell_removes_startup_hooks_before_bash_starts(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'must-not-exist'
            startup = Path(directory) / 'startup.sh'
            startup.write_text('touch ' + shlex.quote(str(marker)) + '\n')
            result = self.invoke('probe', startup_env={'BASH_ENV': str(startup),
                                                      'ENV': str(startup)})
            self.assertFalse(marker.exists(), 'Bash sourced a startup file before dispatch')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), ['/usr/local/bin/slickflow-deploy', 'probe'])

    def test_caller_shell_startup_files_cannot_execute(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'must-not-exist'
            startup = Path(directory) / 'startup.sh'
            startup.write_text('touch ' + shlex.quote(str(marker)) + '\n')
            with patch.dict(os.environ, {'BASH_ENV': str(startup), 'ENV': str(startup)}):
                result = self.invoke('probe')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(result.stdout.splitlines(), ['/usr/local/bin/slickflow-deploy', 'probe'])

    def test_script_extraction_tolerates_yaml_indentation_and_chomping(self):
        source = WORKFLOW.read_text()
        reformatted = textwrap.indent(source, '    ').replace('run: |\n', 'run: |- # literal script\n')
        self.assertEqual(workflow_script(source), workflow_script(reformatted))
        self.assertEqual(workflow_script(source), workflow_script(source.replace("\n", "\r\n")))
        self.assertEqual(workflow_script('run: |\n  echo safe\nnext: value\n'), 'echo safe\n')
        with self.assertRaises(ValueError):
            workflow_script('run: |\n  echo one\nrun: |\n  echo two\n')

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
                self.assertEqual(result.stdout, '')
                self.assertTrue(result.stderr)

    def test_deploy_rejects_missing_malformed_or_shell_input(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'must-not-exist'
            values = ['', 'a' * 31, 'a' * 33, 'A' * 32, '../release',
                      'a' * 32 + '\n', f'$(touch {marker})', f'; touch {marker}']
            for release in values:
                with self.subTest(release=release):
                    result = self.invoke('deploy', release)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, '')
                    self.assertTrue(result.stderr)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
