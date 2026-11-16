import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('verified', Path(__file__).resolve().parents[1] / 'verified_control_plane_artifacts.py')
VERIFIED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIED)


class VerifiedArtifactsTest(unittest.TestCase):
    def setUp(self):
        self.revision = 'a' * 40
        self.url = 'https://github.com/skizzay/slickflow/actions/runs/123'
        self.run = {'id': 123, 'run_attempt': 2, 'repository': {'full_name': 'skizzay/slickflow'},
                    'path': '.github/workflows/control-plane.yaml', 'status': 'completed',
                    'conclusion': 'success', 'event': 'push', 'head_branch': 'epic/108',
                    'head_sha': self.revision, 'html_url': self.url}
        self.records = {arch: {'architecture': arch, 'revision': self.revision,
                              'run_url': self.url, 'run_attempt': '2',
                              'images': {target: f'ghcr.io/skizzay/slickflow-{target}@sha256:' + digit * 64
                                         for target in ('runtime', 'migration')}}
                        for arch, digit in [('amd64', 'b'), ('arm64', 'c')]}

    def test_selects_native_split_host_pair(self):
        pair = VERIFIED.select_pair(self.run, self.records, self.revision)
        self.assertEqual(pair['runtime'], self.records['arm64']['images']['runtime'])
        self.assertEqual(pair['migration'], self.records['amd64']['images']['migration'])

    def test_failed_untrusted_or_wrong_revision_run_is_rejected(self):
        for field, value in [('status', 'in_progress'), ('conclusion', 'failure'),
                             ('event', 'pull_request'), ('head_branch', 'feature/untrusted'),
                             ('head_sha', 'b' * 40), ('path', 'other.yaml')]:
            with self.subTest(field=field):
                run = dict(self.run, **{field: value})
                with self.assertRaises(ValueError):
                    VERIFIED.select_pair(run, self.records, self.revision)

    def test_mixed_attempt_architecture_revision_or_mutable_digest_rejected(self):
        for field, value in [('run_attempt', '1'), ('architecture', 'arm64'),
                             ('revision', 'd' * 40), ('run_url', self.url + '4')]:
            with self.subTest(field=field):
                records = copy.deepcopy(self.records)
                records['amd64'][field] = value
                with self.assertRaises(ValueError):
                    VERIFIED.select_pair(self.run, records, self.revision)
        for image in ['ghcr.io/skizzay/slickflow-migration:latest',
                      'ghcr.io/other/image@sha256:' + 'e' * 64]:
            with self.subTest(image=image):
                records = copy.deepcopy(self.records)
                records['amd64']['images']['migration'] = image
                with self.assertRaises(ValueError):
                    VERIFIED.select_pair(self.run, records, self.revision)


if __name__ == '__main__':
    unittest.main()
