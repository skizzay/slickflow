#!/usr/bin/env python3
"""Select a split-host pair only from a completed trusted publication run."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

REPOSITORY = 'skizzay/slickflow'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def select_pair(run, records, expected_revision):
    require(re.fullmatch(r'[0-9a-f]{40}', expected_revision), 'Expected full lowercase revision')
    require(run.get('repository', {}).get('full_name') == REPOSITORY, 'Wrong publication repository')
    require(run.get('path') == '.github/workflows/control-plane.yaml', 'Wrong publication workflow')
    require(run.get('status') == 'completed' and run.get('conclusion') == 'success',
            'Publication must have completed successfully')
    require(run.get('event') in ('push', 'workflow_dispatch') and
            run.get('head_branch') in ('epic/108', 'main'), 'Untrusted publication source')
    require(run.get('head_sha') == expected_revision, 'Publication revision differs from approval')
    run_url = f"https://github.com/{REPOSITORY}/actions/runs/{run['id']}"
    require(run.get('html_url') == run_url, 'Wrong publication run URL')
    for arch in ('amd64', 'arm64'):
        record = records[arch]
        require(record.get('revision') == expected_revision and record.get('architecture') == arch,
                'Provenance revision/architecture mismatch')
        require(record.get('run_url') == run_url and
                str(record.get('run_attempt')) == str(run['run_attempt']), 'Provenance run/attempt mismatch')
        require(set(record.get('images', {})) == {'runtime', 'migration'}, 'Incomplete published pair')
        for target, image in record['images'].items():
            require(isinstance(image, str) and re.fullmatch(
                rf'ghcr.io/{REPOSITORY}-{target}@sha256:[0-9a-f]{{64}}', image),
                'Expected immutable image from the approved registry repository')
    return {'revision': expected_revision, 'publication_run': run_url,
            'publication_attempt': run['run_attempt'],
            'runtime': records['arm64']['images']['runtime'],
            'migration': records['amd64']['images']['migration']}


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True, timeout=120)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=int)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    require(args.run > 0, 'Expected a positive publication run ID')
    run = json.loads(gh('api', f'repos/{REPOSITORY}/actions/runs/{args.run}'))
    # Refuse failed/wrong-source runs before downloading any records.
    require(run.get('status') == 'completed' and run.get('conclusion') == 'success',
            'Publication must have completed successfully')
    records = {}
    with tempfile.TemporaryDirectory() as temporary:
        for arch in ('amd64', 'arm64'):
            directory = Path(temporary) / arch
            gh('run', 'download', str(args.run), '--repo', REPOSITORY, '--name',
               f"control-plane-provenance-{arch}-{run['run_attempt']}", '--dir', str(directory))
            records[arch] = json.loads((directory / f'provenance-{arch}.json').read_text())
    print(json.dumps(select_pair(run, records, args.revision), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Artifact verification failed: {error}')
