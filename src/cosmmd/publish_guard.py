"""Audit the actual Git index and reachable history, not just .gitignore.

Media must be individually listed with hashes in docs/media/manifest.json.
This is a focused release guard, not a complete secret-detection product.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

DENIED = {'.vmd', '.vpd', '.pmx', '.pmd', '.fbx', '.glb', '.gltf', '.obj', '.mtl',
          '.bvh', '.stl', '.abc', '.zip', '.7z', '.rar', '.tar', '.gz', '.mp4', '.mov',
          '.mp3', '.wav', '.ogg', '.flac', '.exr', '.hdr', '.key', '.pem', '.log'}
MEDIA = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
PRIVATE_DIRS = {'private', 'inputs', 'work', 'runs', 'output', 'outputs', 'downloads', 'vendor', '.venv'}
SECRETS = [re.compile(rb'tsk[_\\]+[A-Za-z0-9_\\-]{24,}'),
           re.compile(rb'gh[pousr]_[A-Za-z0-9]{25,}'),
           re.compile(rb'github_pat_[A-Za-z0-9_]{30,}'),
           re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
           re.compile(rb'https://[^\s/@]+:[^\s/@]+@github\.com'),
           re.compile(rb'(?:/Users/|/home/)[A-Za-z0-9._-]+/')]
MAGIC = (b'BLENDER', b'glTF', b'Vocaloid Motion Data', b'PMX ', b'Pmd', b'Kaydara FBX', b'PK\x03\x04')


def violations(path, data, approved):
    p = Path(path)
    errors = []
    if p.is_absolute() or '..' in p.parts or any(part in PRIVATE_DIRS for part in p.parts[:-1]):
        errors.append('private path')
    if p.suffix.lower() in DENIED or '.blend' in p.name.lower() or (p.name.startswith('.env') and p.name != '.env.example'):
        errors.append('private/binary format')
    if data.startswith(MAGIC):
        errors.append('model/motion/archive content signature')
    if any(pattern.search(data) for pattern in SECRETS):
        errors.append('potential credential or private absolute path')
    if len(data) > 12 * 1024 * 1024:
        errors.append('file exceeds 12 MB presentation limit')
    if p.suffix.lower() in MEDIA:
        entry = approved.get(path)
        allowed_hashes = [entry.get('sha256'), *entry.get('previous_sha256', [])] if entry else []
        if not entry or hashlib.sha256(data).hexdigest() not in allowed_hashes or not entry.get('rights'):
            errors.append('media missing matching hash and rights note')
    elif b'\x00' in data[:8192]:
        errors.append('unexpected binary content')
    return errors


def audit(root, history=True):
    root = Path(root)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL)
    try:
        manifest = json.loads(git('show', ':docs/media/manifest.json'))
    except subprocess.CalledProcessError:
        manifest = {}
    approved = manifest.get('files', {})
    findings = []
    checked = 0
    for raw in git('ls-files', '--stage', '-z').split(b'\x00'):
        if not raw:
            continue
        meta, name = raw.split(b'\t', 1)
        mode, oid, stage = meta.decode().split()
        path = name.decode()
        if mode != '100644' and mode != '100755':
            findings.append(f'{path}: unsupported index mode (symlinks/submodules are not published)')
            continue
        data = git('cat-file', 'blob', oid)
        for reason in violations(path, data, approved):
            findings.append(f'{path}: {reason}')
        checked += 1
    if history:
        for line in git('rev-list', '--objects', '--all').splitlines():
            parts = line.decode().split(' ', 1)
            if len(parts) != 2:
                continue
            oid, path = parts
            if git('cat-file', '-t', oid).strip() != b'blob':
                continue
            data = git('cat-file', 'blob', oid)
            # Earlier media must also have an explicitly reviewed hash in the manifest.
            for reason in violations(path, data, approved):
                findings.append(f'history {path}: {reason}')
    return {'checked_index_files': checked, 'findings': sorted(set(findings)), 'ok': not findings}
