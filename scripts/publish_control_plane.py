"""Publish the locally verified control-plane pair from the guarded CI checkout."""

import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory

from control_plane_registry import BINDING_FIELD, PIN_KEY, ROLES, Registry, RegistryError, is_digest


def check_source():
    repository = os.environ.get("GITHUB_REPOSITORY")
    revision = os.environ.get("GITHUB_SHA", "")
    if repository != "skizzay/slickflow" or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RegistryError("Publication requires skizzay/slickflow and a full lowercase commit SHA.")
    if (
        os.environ.get("GITHUB_REF") != "refs/heads/main"
        or os.environ.get("GITHUB_EVENT_NAME") not in ("push", "workflow_dispatch")
    ):
        raise RegistryError("Publication requires a push or manual dispatch on refs/heads/main.")
    checkout = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, timeout=10,
    ).stdout.strip()
    if checkout != revision.encode():
        raise RegistryError("Publication checkout does not match the selected commit.")


def docker(args, message, *, docker_config=None, input_bytes=None):
    command = ["docker"]
    if docker_config:
        command += ["--config", docker_config]
    try:
        return subprocess.run(
            command + args, input=input_bytes, capture_output=True, check=True, timeout=600,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        raise RegistryError(message) from None


def unique_fields(pairs):
    data = dict(pairs)
    if len(data) != len(pairs):
        raise ValueError("Duplicate fields")
    return data


def read_credentials(path_value, approved_pin):
    message = "A protected Forgejo publication credential file is required."
    try:
        path = Path(path_value or "")
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise RegistryError(message)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.geteuid():
                raise RegistryError(message)
            data = handle.read(4097)
        if len(data) > 4096:
            raise RegistryError(message)
        credentials = json.loads(data, object_pairs_hook=unique_fields)
    except RegistryError:
        raise
    except (OSError, ValueError, RuntimeError):
        raise RegistryError(message) from None
    if not isinstance(credentials, dict) or credentials.keys() != {"registry", "username", "token", BINDING_FIELD}:
        raise RegistryError(message)
    username = credentials["username"]
    token = credentials["token"]
    if (
        not isinstance(username, str)
        or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", username)
        or not isinstance(token, str)
        or not re.fullmatch(r"[!-~]{1,2048}", token)
    ):
        raise RegistryError(message)
    registry = Registry.parse(credentials["registry"])
    registry.require_pin(approved_pin)
    registry.require_pin(credentials[BINDING_FIELD])
    return registry, username, token


def publish():
    env = os.environ
    revision = env["GITHUB_SHA"]
    arch = env.get("SLICKFLOW_PUBLISH_ARCH")
    if arch not in ("amd64", "arm64"):
        raise RegistryError("Publication supports only native amd64 or arm64.")
    summary_path = env.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        raise RegistryError("A pipeline summary path is required.")
    run = env.get("GITHUB_RUN_ID", "")
    attempt = env.get("GITHUB_RUN_ATTEMPT", "")
    if not all(re.fullmatch(r"[1-9][0-9]{0,19}", number) for number in (run, attempt)):
        raise RegistryError("A valid Actions run ID and attempt are required.")

    manifest = Path(f"provenance-{arch}.json")
    manifest.unlink(missing_ok=True)

    local_tag = f"{revision}-{arch}"
    for role in ROLES:
        message = f"The local {arch} {role} image does not match the reviewed revision, platform and user."
        fmt = '{{index .Config.Labels "org.opencontainers.image.revision"}} {{.Os}}/{{.Architecture}} {{.Config.User}}'
        actual = docker(["image", "inspect", f"slickflow-{role}:{local_tag}", "--format", fmt], message)
        if actual.strip() != f"{revision} linux/{arch} 10001:10001".encode():
            raise RegistryError(message)

    registry, username, token = read_credentials(env.get("SLICKFLOW_REGISTRY_AUTH_FILE"), env.get(PIN_KEY))
    images = {}
    with TemporaryDirectory(prefix="slickflow-registry-") as docker_config:
        # An auth entry prevents the CLI from selecting a default persistent credential helper.
        Path(docker_config, "config.json").write_text(json.dumps({"auths": {registry.host: {}}}))
        docker(
            ["login", "--username", username, "--password-stdin", registry.host],
            "Forgejo authentication failed. Check the approved publisher credentials, TLS and connectivity.",
            docker_config=docker_config,
            input_bytes=token.encode() + b"\n",
        )
        for role in ROLES:
            repository = registry.repository(role)
            tagged = f"{repository}:{local_tag}"
            docker(
                ["tag", f"slickflow-{role}:{local_tag}", tagged],
                f"Could not tag the verified {arch} {role} image.",
                docker_config=docker_config,
            )
            docker(
                ["push", tagged],
                f"Forgejo did not confirm the {arch} {role} push. Check package access and rerun all jobs.",
                docker_config=docker_config,
            )
            message = f"Forgejo did not provide one immutable digest for the {arch} {role} image."
            raw = docker(
                ["image", "inspect", tagged, "--format", "{{json .RepoDigests}}"],
                message,
                docker_config=docker_config,
            )
            try:
                references = json.loads(raw)
            except (ValueError, RecursionError):
                raise RegistryError(message) from None
            prefix = repository + "@"
            digests = [
                ref[len(prefix):] for ref in references
                if isinstance(ref, str) and ref.startswith(prefix) and is_digest(ref[len(prefix):])
            ] if isinstance(references, list) else []
            if len(digests) != 1:
                raise RegistryError(message)
            images[role] = digests[0]

    if images["runtime"] == images["migration"]:
        raise RegistryError("Forgejo must provide different runtime and migration digests.")

    record = {
        "revision": revision,
        "architecture": arch,
        "run_url": f"https://github.com/{env['GITHUB_REPOSITORY']}/actions/runs/{run}",
        "run_attempt": attempt,
        BINDING_FIELD: registry.binding_sha256,
        "images": images,
    }
    data = json.dumps(record, indent=2) + "\n"
    manifest.write_text(data)
    with open(summary_path, "a") as summary:
        summary.write("### Verified control-plane artifacts\n\n```json\n" + data + "```\n")


if __name__ == "__main__":
    try:
        os.chdir(Path(__file__).resolve().parents[1])
        check_source()
        if sys.argv[1:] != ["--check-source"]:
            if len(sys.argv) != 1:
                raise RegistryError("Unsupported publication options.")
            publish()
    except RegistryError as error:
        sys.exit(str(error))
    except (OSError, ValueError, subprocess.SubprocessError, RecursionError):
        sys.exit("Publication evidence or configuration is unavailable. Check the protected inputs and rerun all jobs.")
