"""Check tracked files and historical Git blobs without printing matched secrets."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import src  # Loads ignored local environment for exact-value checks.

PATTERNS = [rb'gsk_[A-Za-z0-9]{20,}', rb'sk-(?:proj-)?[A-Za-z0-9_-]{24,}',
            rb'AIza[A-Za-z0-9_-]{30,}', rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def unsafe(content):
    configured = [os.getenv(k, '').encode() for k in ['GROQ_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_API_KEY']]
    return any(re.search(p, content) for p in PATTERNS) or any(k and len(k) > 12 and k in content for k in configured)


def main():
    failures = []
    names = git('ls-files', '-z').decode().split('\0')
    for name in filter(None, names):
        if name == '.env' or name.startswith(('.venv/', 'node_modules/', 'tmp/')):
            failures.append('Forbidden tracked path: ' + name)
        path = ROOT / name
        if path.is_file() and unsafe(path.read_bytes()):
            failures.append('Potential secret in tracked file: ' + name)
    blobs = 0
    for line in git('rev-list', '--objects', '--all').decode().splitlines():
        object_id = line.split(' ', 1)[0]
        if git('cat-file', '-t', object_id).strip() == b'blob':
            blobs += 1
            if unsafe(git('cat-file', 'blob', object_id)):
                failures.append('Potential secret in historical blob: ' + object_id)
    for failure in failures:
        print(failure)
    if not failures:
        print(f'Secret check passed: tracked files and {blobs} historical blobs; no matched values printed.')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
