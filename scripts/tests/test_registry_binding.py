"""Exercise the shared registry identity and host preflight boundary."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from control_plane_registry import BINDING_KEY, PIN_KEY, Registry, RegistryError, check_host_image


BINDING = "forgejo.private.invalid/synthetic-namespace"
PIN = "sha256:" + hashlib.sha256(BINDING.encode("utf-8")).hexdigest()
MANIFEST = "sha256:" + "a" * 64


class RegistryBindingTest(unittest.TestCase):
    def test_binding_pins_the_exact_lowercase_authority_and_namespace(self):
        registry = Registry.parse(BINDING)
        self.assertEqual(registry.binding_sha256, PIN)
        registry.require_pin(PIN)
        with self.assertRaisesRegex(RegistryError, "differs from the approved binding"):
            Registry.parse(BINDING + "-other").require_pin(PIN)

    def test_rejects_invalid_and_historical_registry_authorities(self):
        for value in (
            None, 42, "", "ghcr.io/skizzay", "GHCR.IO/skizzay", "ghcr.io./skizzay",
            "localhost/tenant", "127.0.0.1/tenant", "https://forgejo.invalid/tenant",
            "registry.invalid:443/tenant", "registry.invalid/tenant/extra", "registry.invalid/Upper",
            "registry.invalid/tenant\n", "someone@registry.invalid/tenant",
            "registry.invalid/tenant?query", "xn--registry.invalid/tenant", "dockeɾ.invalid/tenant",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(RegistryError, "approved Forgejo registry"):
                Registry.parse(value)

    def test_host_role_uses_approved_binding_and_ignores_other_role(self):
        registry = Registry.parse(BINDING)
        for role in ("runtime", "migration"):
            key = f"SLICKFLOW_{role.upper()}_IMAGE"
            with self.subTest(role=role), patch.dict(os.environ, {
                BINDING_KEY: BINDING, PIN_KEY: PIN, key: registry.reference(role, MANIFEST),
            }, clear=True):
                check_host_image(role)

    def test_host_rejects_unknown_repositories_tags_and_local_images_before_docker(self):
        for mode in ("runtime", "runtime-webhook", "migration"):
            role = mode.split("-")[0]
            other = "migration" if role == "runtime" else "runtime"
            cases = [
                (f"{BINDING}/slickflow-{role}:latest", "immutable registry digest"),
                (MANIFEST, "immutable registry digest"),
                (f"ghcr.io/skizzay/slickflow-{role}@{MANIFEST}", "approved Forgejo role repository"),
                (f"unapproved.invalid/synthetic-namespace/slickflow-{role}@{MANIFEST}", "approved Forgejo role repository"),
                (f"forgejo.private.invalid/other/slickflow-{role}@{MANIFEST}", "approved Forgejo role repository"),
                (f"{BINDING}/slickflow-{other}@{MANIFEST}", "approved Forgejo role repository"),
            ]
            for reference, message in cases:
                with self.subTest(mode=mode, reference=reference):
                    result = subprocess.run(
                        ["bash", str(SCRIPTS / "check-control-plane-host.sh"), mode],
                        env=dict(os.environ, **{BINDING_KEY: BINDING, PIN_KEY: PIN,
                            f"SLICKFLOW_{role.upper()}_IMAGE": reference}),
                        cwd="/tmp", capture_output=True, text=True, check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message, result.stderr)
                    for value in BINDING.split("/"):
                        self.assertNotIn(value, result.stderr)

    def test_missing_or_mismatched_host_pin_fails_closed(self):
        for pin in ("", MANIFEST):
            with self.subTest(pin=pin), patch.dict(os.environ, {
                BINDING_KEY: BINDING, PIN_KEY: pin,
                "SLICKFLOW_RUNTIME_IMAGE": Registry.parse(BINDING).reference("runtime", MANIFEST),
            }, clear=True), self.assertRaisesRegex(RegistryError, "differs from the approved binding"):
                check_host_image("runtime")


if __name__ == "__main__":
    unittest.main()
