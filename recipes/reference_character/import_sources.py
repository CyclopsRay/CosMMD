"""Initialize local-only source files for the fitted reference-character recipe."""
import os
from pathlib import Path

import bpy

ROOT = Path(os.environ['COSMMD_RUN']).resolve()
for directory in ['work', 'source', 'output']:
    (ROOT / directory).mkdir(parents=True, exist_ok=True)

for filename, blend_name in [('source.glb', 'source/Source_High.blend'),
                             ('rigged.glb', 'work/rig_imported.blend')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / filename))
    if filename == 'source.glb':
        body = max((ob for ob in bpy.context.scene.objects if ob.type == 'MESH'),
                   key=lambda ob: len(ob.data.vertices))
        body.name = 'Source_High'
    else:
        images = [im for im in bpy.data.images if im.size[0] and im.size[1]]
        # Resolve the image feeding Base Color instead of guessing by file order.
        candidates = []
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for link in mat.node_tree.links:
                if link.to_socket.name == 'Base Color' and link.from_node.type == 'TEX_IMAGE':
                    candidates.append(link.from_node.image)
        if not candidates:
            raise RuntimeError('Base color image requires manual identification; do not guess.')
        sample = candidates[0].copy()
        sample.filepath_raw = str(ROOT / 'work/basecolor_sample.png')
        sample.file_format = 'PNG'
        sample.save()
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / blend_name))
