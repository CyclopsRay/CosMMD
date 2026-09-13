"""Tripo v3 adapter. Credentials are never sent to asset-download hosts.

POSTs are intentionally not retried: a timeout may follow a successful charge.
The journal records intent before submission, so ambiguous requests stop safely.
"""
import hashlib
import json
import mimetypes
import os
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

BASE = 'https://openapi.tripo3d.ai/v3'


class TripoError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TripoError('Unexpected API redirect; refusing to forward credentials.')


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.partial.json')
    temporary.write_text(json.dumps(value, indent=2))
    os.chmod(temporary, 0o600)
    temporary.replace(path)


class TripoClient:
    def __init__(self, key=None, timeout=90):
        self.key = key or os.environ.get('TRIPO_API_KEY')
        if not self.key:
            raise TripoError('Set TRIPO_API_KEY in your environment.')
        self.timeout = timeout

    def request(self, method, endpoint, payload=None, body=None, content_type='application/json'):
        if not endpoint.startswith('/') or '..' in endpoint or '://' in endpoint:
            raise ValueError('Expected an API path')
        if payload is not None:
            body = json.dumps(payload).encode()
        req = Request(BASE + endpoint, data=body, method=method,
                      headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': content_type})
        try:
            with build_opener(NoRedirect()).open(req, timeout=self.timeout) as response:
                value = json.load(response)
        except HTTPError as exc:
            raise TripoError(f'Tripo HTTP {exc.code}; request/response contents omitted.') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise TripoError('Tripo request failed; do not blindly resubmit a paid task.') from None
        if value.get('code') != 0:
            raise TripoError(f"Tripo error code {value.get('code')}; check the provider console.")
        return value['data']

    def upload_image(self, path):
        path = Path(path)
        if path.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
            raise ValueError('Use one JPEG or PNG image.')
        data = path.read_bytes()
        if len(data) > 20 * 1024 * 1024:
            raise ValueError('Image exceeds 20 MB.')
        boundary = uuid.uuid4().hex
        # Neutral filename avoids exposing the original local filename.
        name = 'reference' + path.suffix.lower()
        mime = mimetypes.guess_type(name)[0]
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
                f'Content-Type: {mime}\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
        return self.request('POST', '/files', body=body,
                            content_type='multipart/form-data; boundary=' + boundary)['file_token']

    def wait(self, task_id, timeout=1800, interval=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.request('GET', '/tasks/' + quote(task_id, safe=''))
            status = result.get('status')
            if status == 'success':
                return result
            if status in {'failed', 'cancelled', 'banned'}:
                raise TripoError(f'Task {status}; inspect the provider console.')
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
        raise TripoError('Task polling timed out. Resume with the existing journal/task ID.')


def submit_once(client, journal, name, endpoint, payload):
    """Reuse a saved task ID; refuse retries after an ambiguous submission."""
    journal = Path(journal)
    state = json.loads(journal.read_text()) if journal.exists() else {}
    signature = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    existing = state.get(name)
    if existing:
        if existing.get('request_sha256') != signature:
            raise TripoError('Changed task parameters; use a different run directory.')
        if existing.get('task_id'):
            return client.wait(existing['task_id'])
        if existing.get('direct_result') is not None:
            return existing['direct_result']
        raise TripoError('Submission outcome unknown. Recover the task ID from the console; do not resubmit.')
    state[name] = {'request_sha256': signature, 'submission': 'pending_or_unknown'}
    atomic_json(journal, state)
    result = client.request('POST', endpoint, payload)
    if 'task_id' in result:
        state[name].update(task_id=result['task_id'], submission='accepted')
        atomic_json(journal, state)
        return client.wait(result['task_id'])
    # rig-check has had both direct and task-shaped responses in provider docs.
    state[name].update(direct_result=result, submission='accepted')
    atomic_json(journal, state)
    return result


def download_model(result, destination):
    url = result.get('output', {}).get('model_url')
    if not url or urlsplit(url).scheme != 'https':
        raise TripoError('No HTTPS model_url in task output; check the API version.')
    destination = Path(destination)
    temporary = destination.with_suffix('.partial')
    # Separate unauthenticated request. Never reuse API Authorization headers.
    with urlopen(url, timeout=180) as response, temporary.open('wb') as stream:
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > 200 * 1024 * 1024:
                raise TripoError('Model download exceeds the 200 MB local limit.')
            stream.write(chunk)
    with temporary.open('rb') as stream:
        if stream.read(4) != b'glTF':
            temporary.unlink()
            raise TripoError('Downloaded data is not a GLB model.')
    temporary.replace(destination)


def generate(image, run, execute=False, model='v3.1-20260211', rig_model='v1.0-20240301'):
    plan = {'image': str(image), 'model': model, 'rig_model': rig_model,
            'stages': ['upload', 'image-to-model', 'rig-check', 'rig'],
            'paid_task_submissions_at_most': 2,
            'note': 'No automatic regeneration. Provider credit costs vary; inspect current pricing.'}
    if not execute:
        return plan
    run = Path(run)
    run.mkdir(parents=True, exist_ok=True)
    lock = run / '.generation.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise TripoError('Run is locked. Verify no process is active before removing a stale lock.') from None
    os.close(fd)
    try:
        client = TripoClient()
        info_path = run / 'input.json'
        signature = hashlib.sha256(Path(image).read_bytes()).hexdigest()
        if info_path.exists():
            info = json.loads(info_path.read_text())
            if info['sha256'] != signature:
                raise TripoError('Input changed; choose another run directory.')
        else:
            info = {'sha256': signature, 'file_token': client.upload_image(image)}
            atomic_json(info_path, info)
        journal = run / 'tasks.json'
        generated = submit_once(client, journal, 'generation', '/generation/image-to-model',
                                {'input': info['file_token'], 'model': model, 'texture': True,
                                 'pbr': True, 'texture_alignment': 'original_image'})
        download_model(generated, run / 'source.glb')
        source_id = json.loads(journal.read_text())['generation']['task_id']
        check = submit_once(client, journal, 'rig_check', '/animations/rig-check', {'input': source_id})
        check = check.get('output', check)
        if check.get('riggable') is not True or check.get('rig_type') != 'biped':
            raise TripoError('Biped rig-check did not pass. Inspect source.glb; no automatic regeneration.')
        rigged = submit_once(client, journal, 'rig', '/animations/rig',
                            {'input': source_id, 'model': rig_model, 'rig_type': 'biped',
                             'spec': 'tripo', 'out_format': 'glb'})
        download_model(rigged, run / 'rigged.glb')
        return {'status': 'generated_and_auto_rigged', 'source': str(run / 'source.glb'),
                'rigged': str(run / 'rigged.glb'), 'next': 'Inspect topology and calibrate before MMD import.'}
    finally:
        lock.unlink(missing_ok=True)
