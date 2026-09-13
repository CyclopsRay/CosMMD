"""Reusable, explicitly selected rig operations. Coordinates are asset-specific.

These helpers never infer that a boot, glove or hair lock should be reconstructed.
Callers select vertices/bones after inspecting the source mesh and reference.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector


def mesh_snapshot(ob):
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    uv = {}
    for layer in me.uv_layers:
        values = np.empty(len(me.loops) * 2, np.float32)
        layer.data.foreach_get('uv', values)
        uv[layer.name] = values
    return co, uv


def assert_surface_unchanged(ob, snapshot):
    co, uv = mesh_snapshot(ob)
    assert np.array_equal(co, snapshot[0]), 'Source vertex coordinates changed'
    assert uv.keys() == snapshot[1].keys(), 'UV layers changed'
    assert all(np.array_equal(values, snapshot[1][name]) for name, values in uv.items()), 'UVs changed'


def transfer_weights(source, target):
    """Preserve target vertices and UVs while transferring from a rigged proxy."""
    before = mesh_snapshot(target)
    for g in source.vertex_groups:
        if not target.vertex_groups.get(g.name):
            target.vertex_groups.new(name=g.name)
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new('CosMMD weights from proxy', 'DATA_TRANSFER')
    mod.object = source
    mod.use_vert_data = True
    mod.data_types_verts = {'VGROUP_WEIGHTS'}
    mod.vert_mapping = 'POLYINTERP_NEAREST'
    mod.layers_vgroup_select_src = 'ALL'
    mod.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    assert_surface_unchanged(target, before)


def add_finger_chain(arm, hand_bone, names, points, roll_axis=(0, 0, 1)):
    """Four fitted joint positions create three bones inside an existing finger."""
    if len(points) != 4 or len(names) != 3:
        raise ValueError('Expected four joint points and three bone names')
    if any(name in arm.data.bones for name in names):
        raise ValueError('Finger bones already exist; do not duplicate them')
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for i, name in enumerate(names):
        bone = arm.data.edit_bones.new(name)
        bone.head, bone.tail = points[i], points[i + 1]
        bone.parent = arm.data.edit_bones[names[i - 1] if i else hand_bone]
        bone.use_connect = bool(i)
        bone.align_roll(Vector(roll_axis))
    bpy.ops.object.mode_set(mode='OBJECT')


def smooth_selected_weights(ob, vertices, groups, iterations=20, strength=.6):
    """Diffuse selected groups along mesh edges; do not bridge geometric finger gaps."""
    before = mesh_snapshot(ob)
    ids = np.array(sorted(set(vertices)), dtype=np.int32)
    if not len(ids):
        raise ValueError('Empty weight selection')
    lookup = {int(v): i for i, v in enumerate(ids)}
    gids = [ob.vertex_groups[name].index for name in groups]
    columns = {g: i for i, g in enumerate(gids)}
    w = np.zeros((len(ids), len(gids)))
    for row, vi in enumerate(ids):
        for group in ob.data.vertices[int(vi)].groups:
            if group.group in columns:
                w[row, columns[group.group]] = group.weight
    totals = w.sum(1)
    pairs = [(lookup[a], lookup[b]) for e in ob.data.edges
             for a, b in [tuple(e.vertices)] if a in lookup and b in lookup]
    if not pairs:
        return
    edges = np.array(pairs)
    degree = np.bincount(edges.ravel(), minlength=len(ids))
    for _ in range(iterations):
        acc = np.zeros_like(w)
        np.add.at(acc, edges[:, 0], w[edges[:, 1]])
        np.add.at(acc, edges[:, 1], w[edges[:, 0]])
        smooth = acc / np.maximum(degree, 1)[:, None]
        smooth[degree == 0] = w[degree == 0]
        w = (1 - strength) * w + strength * smooth
    w *= (totals / np.maximum(w.sum(1), 1e-12))[:, None]
    for row, vi in enumerate(ids):
        for gid, value in zip(gids, w[row]):
            ob.vertex_groups[gid].add([int(vi)], float(value), 'REPLACE')
    assert_surface_unchanged(ob, before)


def setup_knee_ik(arm, thigh_name, calf_name, target_name, preferred_degrees=25, maximum_degrees=150):
    """For a calibrated local-X knee hinge. Verify axis and sign before calling."""
    thigh, calf = arm.data.bones[thigh_name], arm.data.bones[calf_name]
    u = (thigh.tail_local - thigh.head_local).normalized()
    v = (calf.tail_local - calf.head_local).normalized()
    axis = calf.matrix_local.to_3x3().col[0].normalized()
    rest = math.atan2(axis.dot(u.cross(v)), u.dot(v))
    pb = arm.pose.bones[calf_name]
    if any(c.type == 'IK' for c in pb.constraints):
        raise ValueError('An IK constraint already exists; review it before replacement')
    pb.lock_ik_y = pb.lock_ik_z = True
    pb.use_ik_limit_x = True
    pb.ik_min_x = -rest + .003
    pb.ik_max_x = math.radians(maximum_degrees) - rest
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(preferred_degrees))
    pb['cosmmd_preferred_bend_degrees'] = float(preferred_degrees)
    constraint = pb.constraints.new('IK')
    constraint.target, constraint.subtarget = arm, target_name
    constraint.chain_count, constraint.iterations = 2, 160
    constraint.use_stretch = False
    return {'rest_degrees': math.degrees(rest), 'minimum': pb.ik_min_x, 'maximum': pb.ik_max_x}


def calibrate_rest_pose(arm, meshes):
    """Bake a reviewed neutral pose into mesh + rest bones together, on a copy."""
    if arm.animation_data and arm.animation_data.action:
        raise ValueError('Calibrate before importing animation')
    for ob in meshes:
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        for mod in list(ob.modifiers):
            if mod.type == 'ARMATURE' and mod.object == arm:
                bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    for ob in meshes:
        mod = ob.modifiers.new('CosMMD deformation', 'ARMATURE')
        mod.object, mod.use_deform_preserve_volume = arm, True
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
