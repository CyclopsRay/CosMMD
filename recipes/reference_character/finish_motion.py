# Reference-character calibration recipe: fitted to the showcase anatomy, not a universal preset.
import os
import bpy,sys,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path(os.environ['COSMMD_RUN']).resolve();sys.path.insert(0,str(Path(__file__).parent))
from scene_common import aim_camera,material
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'work/Motion_Raw.blend'))
s=bpy.context.scene;arm=bpy.data.objects['Rig'];body=bpy.data.objects['Character'];N=s.frame_end;meshes=[body,bpy.data.objects['Leg_L'],bpy.data.objects['Leg_R']]
action=arm.animation_data.action;action.name='Licensed_MMD_Body_And_Fingers';action.use_fake_user=True
bag=action.layers[0].strips[0].channelbags[0]
def curve(path,index,frames,values):
    fc=bag.fcurves.find(path,index=index) or bag.fcurves.new(path,index=index)
    fc.keyframe_points.clear();fc.keyframe_points.add(len(frames))
    xy=np.column_stack((frames,values)).astype(np.float32).ravel();fc.keyframe_points.foreach_set('co',xy)
    for k in fc.keyframe_points:k.interpolation='LINEAR'
    fc.update()

feet={};rest_inv={};locs={};lifts={}
for side in ['L','R']:
    leg=bpy.data.objects['Leg_'+side];idx=leg.vertex_groups[side+'_Foot'].index
    pts=[list(v.co) for v in leg.data.vertices if v.co.z<.085 and any(w.group==idx and w.weight>.9 for w in v.groups)]
    feet[side]=np.array(pts);rest_inv[side]=arm.data.bones[side+'_Foot'].matrix_local.inverted()
    locs[side]=np.zeros((N,3));lifts[side]=np.zeros(N)
heads=np.zeros((N,3));hips=np.zeros((N,3));pelvis=np.zeros((N,4));prev=None
for ob in meshes:ob.hide_viewport=True
floor=bpy.data.objects['Studio_Floor'].location.z+.002
for frame in range(1,N+1):
    s.frame_set(frame);i=frame-1
    q=arm.pose.bones['Head'].matrix.to_quaternion()
    if prev:
        dq=prev.rotation_difference(q)
        if dq.w<0:dq.negate()
        heads[i]=np.array(q@dq.axis)*dq.angle
    prev=q.copy();hips[i]=arm.pose.bones['Hip'].head;pelvis[i]=arm.pose.bones['Pelvis'].matrix.to_quaternion()
    for side in ['L','R']:
        m=np.array(arm.pose.bones[side+'_Foot'].matrix@rest_inv[side])
        bottom=float((feet[side]@m[:3,:3].T+m[:3,3])[:,2].min())
        c=arm.pose.bones[side+'_Foot_IK'];lift=max(0,floor-bottom) if c.get('IK_enabled',1)>.5 else 0
        lifts[side][i]=lift
        locs[side][i]=np.array(c.location)+np.array(c.bone.matrix_local.to_3x3().inverted()@Vector((0,0,lift)))
    if frame%1000==0:print('COLLECTED',frame,flush=True)
for ob in meshes:ob.hide_viewport=False
frames=np.arange(1,N+1)
for side in ['L','R']:
    for axis in range(3):curve(f'pose.bones["{side}_Foot_IK"].location',axis,frames,locs[side][:,axis])

# Small damped secondary animation, baked as regular keys; no Python handlers or live physics required.
velocity=np.diff(hips,axis=0,prepend=hips[:1]);accel=np.diff(velocity,axis=0,prepend=velocity[:1])
sample=np.unique(np.r_[np.arange(0,N,3),N-1]);keyframes=sample+1
secondary={}
for pb in arm.pose.bones:
    if not pb.name.startswith(('Hair_','Skirt_')):continue
    pb.rotation_mode='XYZ';values=np.zeros((N,3));state=np.zeros(3);speed=np.zeros(3)
    inv=np.array(pb.bone.matrix_local.to_3x3().inverted())
    hair=pb.name.startswith('Hair_');depth=int(pb.name[-2:]);limit=math.radians((1+depth) if hair else 3)
    for i in range(N):
        if hair:drive=inv@(-heads[i]*(.5+.2*depth))
        else:drive=inv@np.array([accel[i,1]*9,-accel[i,0]*9,0])
        drive=np.clip(drive,-limit,limit)
        speed=(speed+(drive-state)*.14)*.70;state=np.clip(state+speed,-limit,limit);values[i]=state
    for axis in range(3):curve(f'pose.bones["{pb.name}"].rotation_euler',axis,keyframes,values[sample,axis])
    secondary[pb.name]=float(np.degrees(np.abs(values).max()))

# A gentle following camera keeps the full body in view as the dancer travels.
cam=s.camera;cam.data.ortho_scale=2.50;cam.animation_data_clear();follow=hips[0,:2].copy()
for i in range(N):
    follow=follow*.96+hips[i,:2]*.04
    if i%6==0 or i==N-1:
        cam.location=(float(follow[0]),float(follow[1]-5.1),1.20)
        cam.keyframe_insert('location',frame=i+1)
cam.location.z=1.20;aim_camera(cam,(cam.location.x,cam.location.y+5.1,.88))
s.frame_start=1;s.frame_end=N;s.render.fps=30;s.frame_step=1;s.sync_mode="FRAME_DROP";s.render.use_persistent_data=False
s['status']='v3: original high-resolution appearance restored, fitted finger bones, corrected limb rig.'
body['limitations']='No facial morphs or audio; complex cloth and hair intersections remain possible.'
back=cam.rotation_euler.to_matrix()@Vector((0,0,5))
if cam.animation_data and cam.animation_data.action:
 for fc in cam.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
  if fc.data_path=='location':
   delta=back[fc.array_index]
   for kp in fc.keyframe_points:kp.co.y+=delta;kp.handle_left.y+=delta;kp.handle_right.y+=delta
s.frame_set(1);s.cycles.samples=24;s.render.resolution_percentage=100
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'output/Dance.blend'))
report={'motion_frames':N,'fps':30,'duration_seconds':N/30,'bones':len(arm.data.bones),'vertices':sum(len(ob.data.vertices) for ob in meshes), 'leg_vertices':{ob.name:len(ob.data.vertices) for ob in meshes[1:]}, 'finger_bones':30,
        'max_foot_contact_adjustment_m':{k:float(v.max()) for k,v in lifts.items()},'secondary_max_degrees':secondary}
(ROOT/'work/finalization_v3.json').write_text(json.dumps(report,indent=2))
print('FINAL_SAVED',json.dumps(report),flush=True)
