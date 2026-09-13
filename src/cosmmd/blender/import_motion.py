"""Import a user-supplied, licensed VMD into a calibrated native Blender rig.

MMD Tools is an external GPL-3.0 dependency; no code or motion is vendored here.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scene', required=True)
    p.add_argument('--motion', required=True)
    p.add_argument('--mapping', required=True)
    p.add_argument('--addon', required=True, help='Directory containing mmd_tools/')
    p.add_argument('--python-deps', help='Optional directory containing external add-on dependencies such as opencc')
    p.add_argument('--armature', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--scale', type=float, required=True)
    p.add_argument('--rights-confirmed', action='store_true')
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not a.rights_confirmed:
        p.error('Confirm applicable motion/tool usage rights with --rights-confirmed')
    if Path(a.output).resolve() == Path(a.scene).resolve():
        p.error('Save to a new file; preserve the calibrated rig')
    sys.path.insert(0, str(Path(a.addon).resolve()))
    if a.python_deps:
        sys.path.insert(0, str(Path(a.python_deps).resolve()))
    import mmd_tools
    mmd_tools.register()
    from mmd_tools.core.vmd.importer import VMDImporter
    from mmd_tools.compat import action_compat
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.scene).resolve()))
    arm = bpy.data.objects[a.armature]
    mapping = json.loads(Path(a.mapping).read_text())
    missing = sorted(set(mapping.values()) - set(arm.pose.bones.keys()))
    if missing:
        raise ValueError(f'Mapping references absent bones: {missing}')
    VMDImporter(str(Path(a.motion).resolve()), scale=a.scale,
                bone_mapper=lambda ob: {jp: ob.pose.bones[name] for jp, name in mapping.items()},
                frame_margin=0, use_nla=False).assign(arm, action_name='Licensed_MMD_Motion')
    curves = list(action_compat.ActionFCurvesCompatibility(arm.animation_data.action))
    for curve in curves:
        if curve.data_path.endswith('.mmd_ik_toggle'):
            curve.data_path = curve.data_path[:-len('.mmd_ik_toggle')] + '["IK_enabled"]'
            for key in curve.keyframe_points:
                key.interpolation = 'CONSTANT'
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = max(1, round(max((k.co.x for fc in curves for k in fc.keyframe_points), default=1)))
    scene.render.fps, scene.render.fps_base = 30, 1
    # Preserve a calibrated preferred bend only when imported calf tracks are identity
    # and the associated IK controls never turn off. Genuine motion is left intact.
    collection = action_compat.ActionFCurvesCompatibility(arm.animation_data.action)
    restored = []
    for pb in arm.pose.bones:
        degrees = pb.get('cosmmd_preferred_bend_degrees')
        if degrees is None:
            continue
        rotation_path = pb.path_from_id('rotation_quaternion')
        rotations = [fc for fc in curves if fc.data_path == rotation_path]
        other_rotations = [fc for fc in curves if fc.data_path.startswith(pb.path_from_id())
                           and ('rotation_euler' in fc.data_path or 'rotation_axis_angle' in fc.data_path)]
        controls = [c.subtarget for c in pb.constraints if c.type == 'IK' and c.target == arm]
        if not controls or other_rotations:
            continue
        ik_paths = {arm.pose.bones[name].path_from_id() + '["IK_enabled"]' for name in controls}
        ik_off = any(key.co.y < .5 for fc in curves if fc.data_path in ik_paths for key in fc.keyframe_points)
        non_identity = any(abs(key.co.y - (1 if fc.array_index == 0 else 0)) > 1e-5
                           for fc in rotations for key in fc.keyframe_points)
        if ik_off or non_identity:
            continue
        for fc in rotations:
            collection.remove(fc)
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(degrees))
        pb.keyframe_insert('rotation_quaternion', frame=1)
        pb.keyframe_insert('rotation_quaternion', frame=scene.frame_end)
        restored.append(pb.name)
        curves = list(collection)
    scene['cosmmd_restored_preferred_bends'] = json.dumps(restored)
    scene['cosmmd_status'] = 'Motion imported; knee, reach, foot contact and visual QA pending'
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))


if __name__ == '__main__':
    main()
