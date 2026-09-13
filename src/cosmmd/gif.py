"""Make a real before/after GIF from rendered frames; no invented output images."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


def durations(count, fps):
    if not 1 <= fps <= 50:
        raise ValueError('GIF frame rate must be between 1 and 50')
    return [round((i + 1) * 100 / fps) * 10 - round(i * 100 / fps) * 10 for i in range(count)]


def encode(frames, output, fps=15):
    frames = list(frames)
    if not frames:
        raise ValueError('No frames')
    sample = Image.new('RGB', (512 * min(12, len(frames)), 512))
    for i in range(min(12, len(frames))):
        im = frames[round(i * (len(frames) - 1) / max(1, min(12, len(frames)) - 1))]
        sample.paste(im.resize((512, 512)), (i * 512, 0))
    # Coverage preserves small costume/skin colors; the common-color allocation
    # keeps the stage gradient smooth. A single palette avoids temporal flicker.
    palette = Image.new('P', (1, 1))
    palette.putpalette(
        sample.quantize(colors=192, method=Image.Quantize.MAXCOVERAGE).getpalette()[:576]
        + sample.quantize(colors=64).getpalette()[:192])
    # Ordered dither stays anchored in screen space, so GIF delta compression
    # does not encode a new error-diffusion pattern across the entire stage.
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6],
                      [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16 - .5
    w, h = frames[0].size
    noise = np.tile(bayer, ((h + 3) // 4, (w + 3) // 4))[:h, :w, None] * 10
    quantized = [Image.fromarray(np.clip(np.asarray(im, dtype=np.float32) + noise,
                        0, 255).astype('uint8')).quantize(palette=palette, dither=Image.Dither.NONE)
                 for im in frames]
    quantized[0].save(output, save_all=True, append_images=quantized[1:],
                      duration=durations(len(frames), fps), loop=0, optimize=True, disposal=1)
    with Image.open(output) as result:
        total = 0
        for i in range(result.n_frames):
            result.seek(i)
            total += result.info.get('duration', 0)
        expected = round(len(frames) * 100 / fps) * 10
        if total != expected:
            raise ValueError(f'GIF duration changed: {total} != {expected}')
        return {'frames': result.n_frames, 'duration_ms': total, 'size': result.size,
                'bytes': Path(output).stat().st_size}


def showcase(reference, directory, output, fps=15, font=None, tpose=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(directory).glob('frame_*.png'))
    if not files:
        raise ValueError('No rendered frames')

    def load_reference(path, name):
        with Image.open(path) as image:
            result = ImageOps.exif_transpose(image).convert('RGB')
        result.thumbnail((1200, 1200))
        result.info.clear()
        result.save(output / name, quality=90)
        return result

    ref = load_reference(reference, 'input-reference.jpg')
    pose = load_reference(tpose, 't-pose.jpg') if tpose else None

    def face(size):
        return ImageFont.truetype(font, size) if font else ImageFont.load_default(size=size)

    def place(image, box):
        x, y, w, h = box
        tile = ImageOps.contain(image, (w, h), Image.Resampling.LANCZOS)
        base.paste(tile, (x + (w - tile.width) // 2, y + (h - tile.height) // 2))

    width, height = (1440, 792) if pose is not None else (1040, 734)
    base = Image.new('RGB', (width, height), '#faf7f2')
    draw = ImageDraw.Draw(base)
    draw.text((35, 22), 'CosMMD', font=face(44), fill='#8e173b')
    draw.text((36, 78), 'One photo. T pose. 3D. In motion.' if pose is not None
              else 'One image. A character in motion.', font=face(23), fill='#30262c')
    draw.line((35, 123, width-35, 123), fill='#d8c7c8', width=1)
    draw.text((36, 143), '01 / ORIGINAL PHOTO', font=face(17), fill='#8e173b')
    if pose is not None:
        place(ref, (36, 236, 280, 420))
        draw.text((358, 143), '02 / T-POSE REFERENCE', font=face(17), fill='#8e173b')
        draw.text((358, 174), 'Nano Banana Pro / Tripo API workflow', font=face(15), fill='#514049')
        place(pose, (358, 232, 432, 432))
        draw.text((36, 684), 'Your single character input', font=face(15), fill='#514049')
        draw.text((358, 684), 'Review likeness, costume and anatomy', font=face(15), fill='#514049')
        rx, ry, rw = 840, 178, 552
        arrows = [(323, 348), (801, 830)]
    else:
        place(ref, (36, 210, 390, 470))
        rx, ry, rw = 488, 184, 510
        arrows = [(439, 478)]
    draw.text((rx, 143), ('03' if pose is not None else '02') + ' / 12-SECOND MMD DANCE',
              font=face(17), fill='#8e173b')
    for start, end in arrows:
        y = 446 if pose is not None else 430
        draw.line((start, y, end, y), fill='#8e173b', width=3)
        draw.polygon([(end, y), (end-8, y-5), (end-8, y+5)], fill='#8e173b')
    draw.text((rx, ry+rw+14), 'TRIPO 3D + BLENDER + MMD / REAL RENDER',
              font=face(15), fill='#514049')
    frames, standalone = [], []
    for path in files:
        with Image.open(path) as image:
            im = image.convert('RGB')
        result = base.copy()
        result.paste(im.resize((rw, rw), Image.Resampling.LANCZOS), (rx, ry))
        frames.append(result)
        standalone.append(im.resize((512, 512), Image.Resampling.LANCZOS))
    report = {'hero': encode(frames, output/'hero.gif', fps),
              'result': encode(standalone, output/'result.gif', fps)}
    frames[min(len(frames)-1, 75)].save(output/'cover.jpg', quality=92)
    (output/'gif-validation.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--reference', required=True)
    p.add_argument('--frames', required=True)
    p.add_argument('--tpose', help='Prepared T-pose image; adds the intermediate panel')
    p.add_argument('--output', required=True)
    p.add_argument('--fps', type=int, default=15)
    p.add_argument('--font')
    a = p.parse_args()
    print(json.dumps(showcase(a.reference, a.frames, a.output, a.fps, a.font, a.tpose), indent=2))
