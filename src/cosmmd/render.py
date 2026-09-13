"""Bounded, resumable frame rendering. Never accepts file size as a quality check."""
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image


def render(blender, scene, output, start, count, step=1, size=720, samples=64, device='CPU'):
    scene, output = Path(scene).resolve(), Path(output).resolve()
    if count < 1 or step < 1 or size < 16 or samples < 1:
        raise ValueError('count, step, size and samples must be positive')
    if not scene.is_file():
        raise FileNotFoundError(scene)
    output.mkdir(parents=True, exist_ok=True)
    signature = {'scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest(),
                 'start': start, 'count': count, 'step': step, 'size': size,
                 'samples': samples, 'device': device, 'worker_sha256': hashlib.sha256(
                     Path(__file__).with_name('blender').joinpath('render_frame.py').read_bytes()).hexdigest()}
    manifest = output / 'render.json'
    if manifest.exists() and json.loads(manifest.read_text()) != signature:
        raise ValueError('Output belongs to different scene/settings. Choose a new directory.')
    manifest.write_text(json.dumps(signature, indent=2))
    worker = Path(__file__).with_name('blender') / 'render_frame.py'
    for index, frame in enumerate(range(start, start + count * step, step)):
        target = output / f'frame_{frame:06d}.png'
        valid = False
        if target.exists():
            try:
                with Image.open(target) as im:
                    im.load()
                    valid = im.size == (size, size)
            except (OSError, ValueError):
                pass
        if not valid:
            with (output / f'frame_{frame:06d}.log').open('w') as log:
                subprocess.run([str(blender), '--factory-startup', '-b', '--python-exit-code', '1', '--python', str(worker), '--',
                                '--scene', str(scene), '--frame', str(frame), '--output', str(target),
                                '--size', str(size), '--samples', str(samples), '--device', device],
                               stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1800)
        (output / 'progress.json').write_text(json.dumps({'complete': index + 1, 'total': count,
                                                        'frame': frame, 'status': 'rendering'}))
        print(f'{index + 1}/{count}', flush=True)
    (output / 'progress.json').write_text(json.dumps({'complete': count, 'total': count, 'status': 'rendered_pending_qa'}))
