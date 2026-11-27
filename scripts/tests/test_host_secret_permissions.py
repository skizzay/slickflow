"""Exercise actual preflight Python with synthetic file metadata, without Docker."""
import os
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/check-control-plane-host.sh'


class HostSecretPermissionsTest(unittest.TestCase):
    def check(self, role, mode, uid, gid, *, file_type=stat.S_IFREG, signing_only=False):
        normalized = 'migration' if role == 'migration' else 'runtime'
        env = {
            'SLICKFLOW_PREFLIGHT_ROLE': normalized,
            'SLICKFLOW_PREFLIGHT_WEBHOOKS': str(role == 'runtime-webhook').lower(),
            'SLICKFLOW_' + normalized.upper() + '_IMAGE': 'example/image@sha256:' + 'a' * 64,
            'SLICKFLOW_' + normalized.upper() + '_PASSWORD_FILE': '/synthetic/password',
            'SLICKFLOW_WEBHOOK_SECRET_FILE': '/synthetic/signing',
            'SLICKFLOW_DB_URL': 'jdbc:postgresql://db.invalid/slickflow?currentSchema=slickflow&sslmode=verify-full&sslrootcert=/run/trust/postgresql-ca.crt',
            'SLICKFLOW_DB_CA_FILE': '/synthetic/ca.crt',
            'SLICKFLOW_CPU_LIMIT': '1',
            'SLICKFLOW_MIGRATION_MEMORY': '1g',
        }
        source = SCRIPT.read_text().split("python3 - <<'PY'\n", 1)[1].split('\nPY\n', 1)[0]

        def metadata(path):
            if signing_only and path != '/synthetic/signing':
                return SimpleNamespace(st_mode=stat.S_IFREG | 0o400, st_uid=10001, st_gid=10001)
            return SimpleNamespace(st_mode=file_type | mode, st_uid=uid, st_gid=gid)

        with patch.dict(os.environ, env, clear=True), \
                patch('os.path.isfile', return_value=True), patch('os.stat', side_effect=metadata), \
                patch('os.lstat', side_effect=metadata):
            exec(compile(source, str(SCRIPT), 'exec'), {})

    def test_only_approved_read_only_ownership_modes_are_accepted(self):
        for role in ('runtime', 'migration', 'runtime-webhook'):
            for mode, uid, gid in [(0o400, 10001, 0), (0o440, 0, 10001),
                                   (0o440, 10001, 10001)]:
                with self.subTest(role=role, mode=oct(mode), uid=uid, gid=gid):
                    self.check(role, mode, uid, gid)

    def test_other_group_write_execute_special_and_wrong_owner_modes_are_rejected(self):
        for role in ('runtime', 'migration', 'runtime-webhook'):
            for mode, uid, gid in [(0o440, 10001, 1000), (0o460, 10001, 1000),
                                   (0o600, 10001, 10001), (0o660, 10001, 10001),
                                   (0o404, 10001, 10001), (0o500, 10001, 10001),
                                   (0o4400, 10001, 10001), (0o400, 0, 10001),
                                   (0o400, 1000, 10001), (0o440, 1000, 10001)]:
                with self.subTest(role=role, mode=oct(mode), uid=uid, gid=gid):
                    with self.assertRaisesRegex(SystemExit, 'must be a regular file'):
                        self.check(role, mode, uid, gid)

    def test_symlink_to_an_otherwise_valid_secret_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, 'must be a regular file'):
            self.check('runtime', 0o400, 10001, 10001, file_type=stat.S_IFLNK)

    def test_signing_secret_is_checked_independently_of_valid_database_secret(self):
        with self.assertRaisesRegex(SystemExit, 'SLICKFLOW_WEBHOOK_SECRET_FILE'):
            self.check('runtime-webhook', 0o440, 10001, 1000, signing_only=True)


if __name__ == '__main__':
    unittest.main()
