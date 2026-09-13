# Reference-character calibration recipe: fitted to the showcase anatomy, not a universal preset.
import os
import bpy, json, math
import numpy as np
from mathutils import Vector, Matrix
from pathlib import Path
ROOT=Path(os.environ['COSMMD_RUN']).resolve()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/Rigged_Base.blend'))
scene=bpy.context.scene;scene.frame_set(1)
arm=bpy.data.objects['Rig'];body=bpy.data.objects['Character']
arm.animation_data_clear()
for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
before={b.name:b.matrix.copy() for b in arm.pose.bones}
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True)
bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
eb=arm.data.edit_bones
def new_control(name,head,tail,parent):
    b=eb.new(name);b.head=head;b.tail=tail;b.parent=eb[parent];b.use_deform=False
    return b
h=eb['Hip'].head.copy()
new_control('MMD_Groove',h,h+Vector((0,0,.12)),'Hip')
for name in ['Waist','Pelvis']:eb[name].parent=eb['MMD_Groove']
for name in [f'Skirt_{j:02}_01' for j in range(1,9)]:eb[name].parent=eb['Pelvis']
for side in ['L','R']:
    foot=eb[f'{side}_Foot'].head.copy();toe=eb[f'{side}_ToeBase'].head.copy()
    knee=eb[f'{side}_Calf'].head.copy()
    new_control(f'{side}_Foot_IK',foot,foot+Vector((0,0,.14)),'Root')
    new_control(f'{side}_Toe_IK',toe,toe+Vector((0,-.08,0)),f'{side}_Foot_IK')
    new_control(f'{side}_Knee_Pole',knee+Vector((0,-.5,0)),knee+Vector((0,-.5,.09)),'Hip')
bpy.ops.object.mode_set(mode='OBJECT')
controls=arm.data.collections.new('MMD Motion Controls')
for b in arm.data.bones:
    if b.name=='MMD_Groove' or b.name.endswith(('_IK','_Pole')):
        controls.assign(b);b.color.palette='THEME02'
for pb in arm.pose.bones:pb.rotation_mode='QUATERNION';pb.matrix_basis=Matrix.Identity(4)

mapping={'全ての親':'Root','センター':'Hip','グルーブ':'MMD_Groove','下半身':'Pelvis',
         '上半身':'Spine01','上半身2':'Spine02','首':'NeckTwist01','頭':'Head'}
for jp,side in [('左','L'),('右','R')]:
    for suffix,bone in [('肩','Clavicle'),('腕','Upperarm'),('腕捩','UpperarmTwist01'),
                        ('ひじ','Forearm'),('手捩','ForearmTwist01'),('手首','Hand'),
                        ('足','Thigh'),('ひざ','Calf'),('足首','Foot'),('つま先','ToeBase'),
                        ('足ＩＫ','Foot_IK'),('つま先ＩＫ','Toe_IK')]:
        mapping[jp+suffix]=f'{side}_{bone}'
for jp,name in mapping.items():arm.pose.bones[name]['MMD_name']=jp
arm['mmd_mapping_json']=json.dumps(mapping,ensure_ascii=False)
arm['vmd_scale']=.0825

scene.frame_start=scene.frame_end=1
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"output/MMD_Prepared.blend"))
(ROOT/"work/mmd_mapping.json").write_text(json.dumps(mapping,ensure_ascii=False,indent=2))
