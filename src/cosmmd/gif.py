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


def showcase(reference, directory, output, fps=15, font=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(directory).glob('frame_*.png'))
    ref = ImageOps.exif_transpose(Image.open(reference)).convert('RGB')
    ref.thumbnail((1200,1200))
    ref.save(output / 'input-reference.jpg', quality=90)
    def face(size):
        return ImageFont.truetype(font, size) if font else ImageFont.load_default(size=size)
    base = Image.new('RGB', (1040, 664), '#faf7f2')
    draw = ImageDraw.Draw(base)
    draw.text((35,22), 'CosMMD', font=face(44), fill='#8e173b')
    draw.text((36,78), 'One image. A character in motion.', font=face(23), fill='#30262c')
    draw.line((35,123,1005,123), fill='#d8c7c8', width=1)
    draw.text((36,143), '01   /   YOUR IMAGE', font=face(17), fill='#8e173b')
    draw.text((488,143), '02   /   A 12-SECOND MMD DANCE', font=face(17), fill='#8e173b')
    tile = ImageOps.contain(ref, (390,390))
    base.paste(tile, (36+(390-tile.width)//2, 225+(390-tile.height)//2))
    draw.line((439,392,470,392), fill='#8e173b', width=3)
    draw.polygon([(470,392),(460,386),(460,398)], fill='#8e173b')
    draw.text((488,622), 'TRIPO  +  BLENDER  /  REAL 3D RENDER', font=face(16), fill='#514049')
    frames, standalone = [], []
    for path in files:
        im = Image.open(path).convert('RGB')
        panel = im.resize((510, 510), Image.Resampling.LANCZOS)
        result = base.copy()
        result.paste(panel, (488, 184))
        # Bottom banner is outside the character viewport; the entire source frame is visible.
        if result.height < 716:
            padded = Image.new('RGB', (1040, 734), '#faf7f2')
            padded.paste(result, (0,0))
            padded.paste(panel, (488,184))
            ImageDraw.Draw(padded).text((488,707), 'TRIPO + BLENDER / REAL 3D RENDER', font=face(15), fill='#514049')
            result = padded
        frames.append(result)
        standalone.append(im.resize((512,512), Image.Resampling.LANCZOS))
    report = {'hero': encode(frames, output/'hero.gif', fps),
              'result': encode(standalone, output/'result.gif', fps)}
    frames[min(len(frames)-1, 75)].save(output/'cover.jpg', quality=92)
    (output/'gif-validation.json').write_text(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--reference', required=True)
    p.add_argument('--frames', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--fps', type=int, default=15)
    p.add_argument('--font')
    a = p.parse_args()
    print(json.dumps(showcase(a.reference, a.frames, a.output, a.fps, a.font), indent=2))
