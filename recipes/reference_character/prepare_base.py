# Reference-character calibration recipe: fitted to the showcase anatomy, not a universal preset.
import os
import bpy, sys, math, json
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT=Path(os.environ['COSMMD_RUN']).resolve()
sys.path.insert(0,str(Path(__file__).parent))
from scene_common import setup_stage
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'work/rig_imported.blend'))
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
body=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
for ob in list(scene.objects):
    if ob not in (arm,body): bpy.data.objects.remove(ob,do_unlink=True)
arm.name='Rig'; body.name='Character'
arm.animation_data_clear()
for pb in arm.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.objects.active=body
bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
dec=body.modifiers.new('Animation mesh reduction','DECIMATE')
dec.ratio=180000/len(body.data.polygons);dec.use_collapse_triangulate=True
bpy.ops.object.modifier_move_up(modifier=dec.name)
bpy.ops.object.modifier_apply(modifier=dec.name)
scale=1.65/.9787595272064209
arm.data.transform(Matrix.Scale(scale,4));body.data.transform(Matrix.Scale(scale,4))
for p in body.data.polygons:p.use_smooth=True
arm.show_in_front=True;arm.data.display_type='OCTAHEDRAL'
body.modifiers[0].use_deform_preserve_volume=True
body['source']='User-supplied source GLB; local only'
body['nominal_height_m']=1.65
body['mesh_note']='Surface mesh includes body, clothing, and hair. Not a complete hidden anatomical body.'
body['finger_note']='Source auto-rig has hand bones but no articulated finger bones.'

# Sample the existing texture only to construct soft vertex masks.
me=body.data; n=len(me.vertices)
co=np.empty(n*3,dtype=np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3)/scale
loops=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',loops)
luv=np.empty(len(me.loops)*2,dtype=np.float32);me.uv_layers.active.data.foreach_get('uv',luv)
uv=np.zeros((n,2),dtype=np.float32);uv[loops]=luv.reshape(-1,2)
img=bpy.data.images.load(str(ROOT/'work/basecolor_sample.png'))
pix=np.array(img.pixels[:],dtype=np.float32).reshape(img.size[1],img.size[0],4)
xy=np.mod(uv,1)*[img.size[0]-1,img.size[1]-1]
colors=pix[xy[:,1].astype(int),xy[:,0].astype(int),:3]
x,y,z=co.T; r,g,b=colors.T
hair=((r-b>.13)&(g>b*1.14)&(g>r*.63)&(z>.645)&(np.abs(x)<.175)).astype(float)
hair[(np.abs(x)<.050)&(z>.807)&(z<.929)&(y<-.02)]=0
edge=np.empty(len(me.edges)*2,dtype=np.int32);me.edges.foreach_get('vertices',edge);edge=edge.reshape(-1,2)
def smooth_mask(v,steps=5):
    degree=np.bincount(edge.ravel(),minlength=n)+1
    for _ in range(steps):
        acc=v.copy(); np.add.at(acc,edge[:,0],v[edge[:,1]]);np.add.at(acc,edge[:,1],v[edge[:,0]])
        v=acc/degree
    return v
hair=smooth_mask(hair)
hair[z<.645]=0

# Garment shell, excluding the exposed legs inside the skirt.
rad=np.sqrt((x/.125)**2+((y+.025)/.105)**2)
skirt=((z>.410)&(z<.635)&(rad>.68)).astype(float)
skirt[((z>.315)&(z<.44)&(np.abs(x)>.108))]=1
skirt=smooth_mask(skirt)
skirt*=np.clip((.635-z)/.075,0,1)

bpy.ops.object.select_all(action='DESELECT');arm.select_set(True)
bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
eb=arm.data.edit_bones
eb['Root'].tail=eb['Root'].head+Vector((0,0,.10*scale))
eb['Hip'].tail=eb['Hip'].head+Vector((0,0,.065*scale))
eb['Head'].tail=Vector((.011,-.028,.956))*scale
chains={}
for side,sx in [('L',1),('R',-1)]:
    for region,sy in [('Front',-.06),('Back',.065)]:
        names=[]
        zs=[.89,.81,.735,.645]
        for i in range(3):
            name=f'Hair_{region}_{side}_{i+1:02}'
            bone=eb.new(name)
            bone.head=Vector((sx*(.088+.009*i),sy,zs[i]))*scale
            bone.tail=Vector((sx*(.088+.009*(i+1)),sy,zs[i+1]))*scale
            bone.parent=eb[names[-1]] if names else eb['Head']
            bone.use_connect=bool(names); names.append(name)
        chains[(side,region)]=names
skirt_chains=[]
for j in range(8):
    angle=2*math.pi*j/8
    names=[]
    for i in range(2):
        name=f'Skirt_{j+1:02}_{i+1:02}'
        bone=eb.new(name)
        a=[(.071,.057,.625),(.13,.10,.515),(.175,.13,.401)]
        rx,ry,h=a[i];tx,ty,tz=a[i+1]
        bone.head=Vector((rx*math.cos(angle),-.025+ry*math.sin(angle),h))*scale
        bone.tail=Vector((tx*math.cos(angle),-.025+ty*math.sin(angle),tz))*scale
        bone.parent=eb[names[-1]] if names else eb['Hip']
        bone.use_connect=bool(names);names.append(name)
    skirt_chains.append(names)
bpy.ops.object.mode_set(mode='OBJECT')
for collname in ['Body','Hair','Skirt']:
    if not arm.data.collections.get(collname):arm.data.collections.new(collname)
for bone in arm.data.bones:
    target='Hair' if bone.name.startswith('Hair_') else 'Skirt' if bone.name.startswith('Skirt_') else 'Body'
    arm.data.collections[target].assign(bone)
    bone.color.palette={'Body':'THEME03','Hair':'THEME09','Skirt':'THEME04'}[target]
for bname in [n for c in chains.values() for n in c]+[n for c in skirt_chains for n in c]:
    body.vertex_groups.new(name=bname)

def replace_blend(index, influence, assignments, base=None):
    if influence<.025:return
    v=me.vertices[index]
    old={g.group:g.weight for g in v.groups}
    for gid,w in old.items():body.vertex_groups[gid].add([index],w*(1-influence),'REPLACE')
    for name,w in assignments.items():
        body.vertex_groups[name].add([index],influence*w+old.get(body.vertex_groups[name].index,0)*(1-influence),'REPLACE')

hair_vertices=skirt_vertices=0
for i in range(n):
    h=float(hair[i])
    if h>.025:
        side='L' if x[i]>=0 else 'R';region='Front' if y[i]<.005 else 'Back'
        chain=chains[(side,region)]
        t=np.clip((.85-z[i])/.08,0,2);a=min(int(t),1);frac=float(t-a)
        weights={chain[a]:1-frac,chain[a+1]:frac}
        # The crown remains attached to Head; lower locks have editable chain controls.
        amount=float(np.clip((.925-z[i])/.055,0,1))*h
        replace_blend(i,amount,weights);hair_vertices+=1
    s=float(skirt[i])
    if s>.025:
        ang=(math.atan2((y[i]+.025)/.105,x[i]/.125)%(2*math.pi))*8/(2*math.pi)
        a=int(ang)%8; f=ang-int(ang); t=float(np.clip((.555-z[i])/.115,0,1))
        weights={}
        for j,aw in [(a,1-f),((a+1)%8,f)]:
            weights[skirt_chains[j][0]]=aw*(1-t)
            weights[skirt_chains[j][1]]=aw*t
        replace_blend(i,.96*s,weights);skirt_vertices+=1

# Clean tiny weights and normalize every vertex after editing masks.
bpy.context.view_layer.objects.active=body
bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
bpy.ops.object.vertex_group_clean(group_select_mode='ALL',limit=.005,keep_single=True)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
for mat in me.materials:
    if mat and mat.use_nodes:
        bs=mat.node_tree.nodes.get('Principled BSDF')
        if bs:bs.inputs['Roughness'].default_value=.78

# A clearly named short diagnostic, not the requested dance.
scene.frame_start=1;scene.frame_end=91
def rotate_world(name,axis,angle):
    pb=arm.pose.bones[name];pb.rotation_mode='QUATERNION'
    q=pb.bone.matrix_local.to_quaternion()
    pb.rotation_quaternion=q.inverted()@Quaternion(Vector(axis),math.radians(angle))@q
for frame in [1,31,61,91]:
    for pb in arm.pose.bones:
        pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion();pb.location=(0,0,0)
    if frame in (31,61):
        rotate_world('L_Upperarm',(0,1,0),40 if frame==31 else -25)
        rotate_world('R_Upperarm',(0,1,0),-40 if frame==31 else -55)
        rotate_world('L_Forearm',(0,0,1),-40 if frame==31 else -20)
        rotate_world('R_Forearm',(0,0,1),40 if frame==31 else 65)
        rotate_world('Head',(0,0,1),-8 if frame==31 else 8)
        if frame==61:
            rotate_world('L_Thigh',(1,0,0),-18)
            rotate_world('L_Calf',(1,0,0),28)
        for j,ns in enumerate(chains.values()):
            for k,name in enumerate(ns):
                arm.pose.bones[name].rotation_quaternion=Quaternion((1,0,0),math.radians((3+k)*(-1 if frame==31 else 1)))
        for j,ns in enumerate(skirt_chains):
            for name in ns:arm.pose.bones[name].rotation_quaternion=Quaternion((0,0,1),math.radians(2*math.sin(j+frame/20)))
    for pb in arm.pose.bones:
        pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
        if pb.name=='Hip':pb.keyframe_insert('location',frame=frame,group=pb.name)
arm.animation_data.action.name='Rig_Check_Only_NOT_Kimiiro';arm.animation_data.action.use_fake_user=True
cam=setup_stage(1.65)
scene['status']='Rigged character with diagnostic poses. Kimiiro motion has not been imported yet.'
scene['secondary_controls']='12 hair bones and 16 skirt bones; weighted controls, not cloth or strand simulation.'
scene['nominal_scale']='1.65 m including hairstyle; chosen working scale, not a measured height.'
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.shading.type='MATERIAL'
bpy.ops.file.pack_all()
out=ROOT/'output/Rigged_Base.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(out))
report={'vertices':len(me.vertices),'triangles':len(me.polygons),'bones':len(arm.data.bones),
        'hair_mask_vertices':hair_vertices,'skirt_mask_vertices':skirt_vertices,
        'height_m':1.65,'motion_imported':False,
        'source_body_bones':41,'hair_bones':12,'skirt_bones':16}
(ROOT/'work/character_build.json').write_text(json.dumps(report,indent=2))
print('CHARACTER_BUILD',json.dumps(report))
