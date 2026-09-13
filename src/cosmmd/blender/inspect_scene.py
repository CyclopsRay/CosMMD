"""Import a GLB or open a blend and report real topology before making repairs."""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np


def inspect(source, output, save=None):
    if Path(source).suffix.lower() == '.blend':
        bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(Path(source).resolve()))
    report = {'blender': bpy.app.version_string, 'meshes': [], 'armatures': []}
    for ob in bpy.context.scene.objects:
        if ob.type == 'ARMATURE':
            report['armatures'].append({'name': ob.name, 'bones': [
                {'name': b.name, 'head': list(b.head_local), 'tail': list(b.tail_local),
                 'parent': b.parent.name if b.parent else None} for b in ob.data.bones]})
        if ob.type != 'MESH':
            continue
        me = ob.data
        coords = np.array([tuple(ob.matrix_world @ v.co) for v in me.vertices])
        parent = list(range(len(me.vertices)))
        def find(a):
            while a != parent[a]:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for e in me.edges:
            a, b = (find(v) for v in e.vertices)
            parent[a] = b
        counts = {}
        for i in range(len(parent)):
            root = find(i)
            counts[root] = counts.get(root, 0) + 1
        report['meshes'].append({'name': ob.name, 'vertices': len(me.vertices),
            'faces': len(me.polygons), 'connected_components': len(counts),
            'largest_components': sorted(counts.values(), reverse=True)[:20],
            'bounds': [coords.min(0).tolist(), coords.max(0).tolist()] if len(coords) else [],
            'uv_layers': [u.name for u in me.uv_layers],
            'color_attributes': [a.name for a in me.color_attributes],
            'materials': [m.name if m else None for m in me.materials],
            'unweighted': sum(not any(g.weight > 0 for g in v.groups) for v in me.vertices)})
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    if save:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(save).resolve()))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--save')
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    inspect(a.source, a.output, a.save)
