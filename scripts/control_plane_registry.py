"""Bind control-plane registry references to the owner-approved Forgejo configuration."""

from dataclasses import dataclass
import hashlib
import os
import re
import sys


ROLES = ("runtime", "migration")
DIGEST = r"sha256:[0-9a-f]{64}"
BINDING_KEY = "SLICKFLOW_REGISTRY"
PIN_KEY = "SLICKFLOW_REGISTRY_BINDING_SHA256"
BINDING_FIELD = "registry_binding_sha256"
DNS_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
NAMESPACE = r"[a-z0-9]+(?:[._-][a-z0-9]+)*"


class RegistryError(ValueError):
    """Invalid registry configuration or evidence with a fixed diagnostic."""


def is_digest(value):
    return isinstance(value, str) and re.fullmatch(DIGEST, value) is not None


@dataclass(frozen=True)
class Registry:
    host: str
    namespace: str

    @classmethod
    def parse(cls, value):
        host, _, namespace = (value if isinstance(value, str) else "").partition("/")
        if (
            len(host) > 253
            or not re.fullmatch(rf"(?:{DNS_LABEL}\.)+{DNS_LABEL}", host)
            or not re.search(r"[a-z]", host.rsplit(".", 1)[-1])
            or any(label.startswith("xn--") for label in host.split("."))
            or host in {"ghcr.io", "docker.io", "index.docker.io", "registry-1.docker.io"}
            or len(namespace) > 63
            or not re.fullmatch(NAMESPACE, namespace)
        ):
            raise RegistryError("An approved Forgejo registry host and namespace are required.")
        return cls(host, namespace)

    def repository(self, role):
        if role not in ROLES:
            raise RegistryError("Unknown control-plane image role.")
        return f"{self.host}/{self.namespace}/slickflow-{role}"

    @property
    def binding_sha256(self):
        binding = f"{self.host}/{self.namespace}"
        return "sha256:" + hashlib.sha256(binding.encode("utf-8")).hexdigest()

    def require_pin(self, pin):
        if self.binding_sha256 != pin:
            raise RegistryError("Forgejo registry configuration differs from the approved binding.")

    def reference(self, role, digest):
        if not is_digest(digest):
            raise RegistryError(f"An immutable manifest digest is required for the {role} image.")
        return f"{self.repository(role)}@{digest}"


def check_host_image(role):
    image = os.environ.get(f"SLICKFLOW_{role.upper()}_IMAGE", "")
    _, _, digest = image.partition("@")
    if not is_digest(digest):
        raise RegistryError("The selected image must be an immutable registry digest reference.")
    registry = Registry.parse(os.environ.get(BINDING_KEY))
    registry.require_pin(os.environ.get(PIN_KEY))
    if image != registry.reference(role, digest):
        raise RegistryError("The selected image does not match the approved Forgejo role repository.")


if __name__ == "__main__":
    try:
        check_host_image(sys.argv[1])
    except RegistryError as error:
        sys.exit(str(error))
