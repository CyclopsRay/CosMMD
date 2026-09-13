"""Scan every frame, then require visual review. Statistics alone are not approval."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def inspect_frames(directory, expected=None, step=None):
    files = sorted(Path(directory).glob('frame_*.png'))
    errors, rows, sizes = [], [], set()
    if not files:
        errors.append('No frames found')
    if expected is not None and len(files) != expected:
        errors.append(f'Expected {expected} frames, found {len(files)}')
    numbers = []
    for path in files:
        try:
            number = int(path.stem.split('_')[-1])
            numbers.append(number)
            with Image.open(path) as im:
                im.load()
                sizes.add(im.size)
                a = np.asarray(im.convert('RGB').resize((160, 160)), dtype=float) / 255
            # Central area includes the character in the supplied studio demo.
            # This is a heuristic: dark costumes must be reviewed, not auto-discarded.
            center = a[25:145, 40:120]
            rows.append({'file': path.name, 'mean': float(a.mean()),
                         'black_fraction': float((a.max(axis=2) < .01).mean()),
                         'subject_black_fraction': float((center.max(axis=2) < .01).mean())})
        except (OSError, ValueError):
            errors.append(f'Unreadable frame: {path.name}')
    if len(sizes) > 1:
        errors.append('Mixed frame dimensions')
    if step and any(b - a != step for a, b in zip(numbers, numbers[1:])):
        errors.append('Frame sequence has gaps or unexpected spacing')
    suspicious = [r['file'] for r in rows if r['mean'] < .015 or r['subject_black_fraction'] > .15]
    return {'count': len(files), 'sizes': sorted(sizes), 'errors': errors,
            'suspicious_frames': suspicious, 'frames': rows,
            'visual_review_required': True,
            'note': 'No flagged frames does not prove correct materials, fingers, cloth, or motion.'}


def contact_sheets(directory, output, per_page=60):
    files = sorted(Path(directory).glob('frame_*.png'))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    sheets = []
    for offset in range(0, len(files), per_page):
        canvas = Image.new('RGB', (1200, 1000), '#eeeeee')
        draw = ImageDraw.Draw(canvas)
        for i, path in enumerate(files[offset:offset + per_page]):
            im = Image.open(path).convert('RGB')
            im.thumbnail((120, 140))
            x, y = (i % 10) * 120, (i // 10) * 165
            canvas.paste(im, (x, y))
            draw.text((x + 3, y + 143), path.stem, fill='black')
        path = output / f'contact_{offset // per_page + 1:02d}.jpg'
        canvas.save(path, quality=90)
        sheets.append(str(path))
    return sheets
