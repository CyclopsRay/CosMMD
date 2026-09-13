"""Validate actual animation transforms; emit a private report without editing the scene."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scene', required=True)
    p.add_argument('--armature', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--mesh', action='append', default=[])
    p.add_argument('--knee', nargs=2, action='append', default=[], metavar=('THIGH', 'CALF'))
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.scene).resolve()))
    scene = bpy.context.scene
    arm = bpy.data.objects[a.armature]
    meshes = [bpy.data.objects[name] for name in a.mesh] if a.mesh else [
        ob for ob in scene.objects if ob.type == 'MESH'
        and any(m.type == 'ARMATURE' and m.object == arm for m in ob.modifiers)]
    report = {'bones': len(arm.data.bones), 'frames': [scene.frame_start, scene.frame_end],
              'fps': scene.render.fps / scene.render.fps_base, 'unweighted': {},
              'nonfinite': [], 'reversed_knees': [], 'invalid_drivers': [],
              'knee_axis_assumption': 'local X, calibrated positive flexion',
              'visual_review_required': True}
    for ob in meshes:
        report['unweighted'][ob.name] = sum(sum(g.weight for g in v.groups) < .99 for v in ob.data.vertices)
        ob.hide_viewport = True
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        for b in arm.pose.bones:
            if not all(math.isfinite(value) for row in b.matrix for value in row):
                report['nonfinite'].append([frame, b.name])
        for thigh_name, calf_name in a.knee:
            thigh, calf = arm.pose.bones[thigh_name], arm.pose.bones[calf_name]
            u, v = (thigh.tail - thigh.head).normalized(), (calf.tail - calf.head).normalized()
            axis = calf.matrix.to_3x3().col[0].normalized()
            angle = math.degrees(math.atan2(axis.dot(u.cross(v)), u.dot(v)))
            if angle < -.5:
                report['reversed_knees'].append([frame, calf.name, angle])
    for ob in scene.objects:
        if ob.animation_data:
            report['invalid_drivers'] += [f'{ob.name}: {d.data_path}' for d in ob.animation_data.drivers if not d.is_valid]
    report['ok'] = not (report['nonfinite'] or report['reversed_knees'] or report['invalid_drivers']
                        or any(report['unweighted'].values()))
    target = Path(a.report)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ['nonfinite','reversed_knees']}))
    if not report['ok']:
        raise RuntimeError('Scene validation failed; inspect the report')


if __name__ == '__main__':
    main()
