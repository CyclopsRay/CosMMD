"""One fresh Blender process per frame prevents cross-frame render-state reuse."""
import argparse
import json
import sys
from pathlib import Path

import bpy


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scene', required=True)
    p.add_argument('--frame', type=int, required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--size', type=int, default=720)
    p.add_argument('--samples', type=int, default=64)
    p.add_argument('--device', choices=['CPU', 'METAL', 'CUDA', 'OPTIX', 'HIP'], default='CPU')
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.scene).resolve()))
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.render.use_persistent_data = False
    s.cycles.device = 'CPU'
    if a.device != 'CPU':
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = a.device
        prefs.get_devices()
        selected = [d for d in prefs.devices if d.type == a.device]
        if not selected:
            raise RuntimeError(f'No {a.device} device; select CPU explicitly.')
        for d in prefs.devices:
            d.use = d in selected
        s.cycles.device = 'GPU'
    s.cycles.samples = a.samples
    s.cycles.adaptive_min_samples = min(16, a.samples)
    s.cycles.use_denoising = True
    s.cycles.denoising_use_gpu = False
    s.render.resolution_x = s.render.resolution_y = a.size
    s.render.resolution_percentage = 100
    s.render.use_sequencer = False
    s.render.image_settings.media_type = 'IMAGE'
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGB'
    s.render.image_settings.color_depth = '8'
    s.frame_set(a.frame)
    target = Path(a.output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.stem + '.partial.png')
    s.render.filepath = str(partial)
    bpy.ops.render.render(write_still=True)
    partial.replace(target)
    print(json.dumps({'frame': a.frame, 'output': str(target), 'status': 'rendered'}))


if __name__ == '__main__':
    main()
