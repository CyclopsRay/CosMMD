# Reference-character calibration recipe: fitted to the showcase anatomy, not a universal preset.
import os
import bpy,bmesh,sys,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(os.environ['COSMMD_RUN']).resolve()
sys.path.insert(0,str(Path(__file__).parent))
from scene_common import aim_camera,material
def smooth(a,b,x):
    t=min(1,max(0,(x-a)/(b-a)));return t*t*(3-2*t)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'work/Source_T.blend'))
s=bpy.context.scene;arm=bpy.data.objects['Rig'];body=bpy.data.objects['Character'];cam=s.camera
arm.animation_data_clear();cam.animation_data_clear();s.frame_set(1)
for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4);pb.rotation_mode='QUATERNION'
for pb in arm.pose.bones:
    for c in list(pb.constraints):pb.constraints.remove(c)
arm.data.pose_position='REST'
meshes=[body,bpy.data.objects['Leg_L'],bpy.data.objects['Leg_R']]

bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='EDIT');eb=arm.data.edit_bones
for name in ['L_Knee_Pole','R_Knee_Pole']:
    if name in eb:eb.remove(eb[name])
mapping=json.loads((ROOT/'work/mmd_mapping.json').read_text());hands={};arm_calibration={}
finger_defs=[('Thumb','親指','親指先'),('Index','人指','人差指先'),('Middle','中指','中指先'),('Ring','薬指','薬指先'),('Pinky','小指','小指先')]
for side,jp,sign in [('L','左',1),('R','右',-1)]:
    hip=Vector((sign*.113,-.041,.915));knee=Vector((sign*.076,-.020,.478));ankle=Vector((sign*.060,.015,.090))
    for name,a,b in [('Thigh',hip,knee),('Calf',knee,ankle)]:
        bone=eb[side+'_'+name];bone.head=a;bone.tail=b;bone.align_roll(Vector((0,1,0)))
    # Restore the verified ankle/toe pivots and controls, which the untouched auto-rig misplaced.
    lower=json.loads((Path(__file__).parent/'feet.json').read_text())
    for part in ['Foot','ToeBase','Foot_IK','Toe_IK']:
        name=side+'_'+part;bone=eb[name];data=lower[name]
        bone.matrix=Matrix(data['matrix']);bone.length=(Vector(data['tail'])-Vector(data['head'])).length
    eb[side+'_Foot'].head=ankle;eb[side+'_Foot'].parent=eb[side+'_Calf'];eb[side+'_Foot'].use_connect=True
    sh=Vector((sign*.170,-.045,1.300));el=Vector((sign*.402,-.022,1.257));wr=Vector((sign*.636,-.018,1.255))
    eb[side+'_Clavicle'].tail=sh
    for name,a,b,parent in [('Upperarm',sh,el,side+'_Clavicle'),('UpperarmTwist01',sh.lerp(el,.50),el,side+'_Upperarm'),
        ('Forearm',el,wr,side+'_UpperarmTwist01'),('ForearmTwist01',el.lerp(wr,.50),wr,side+'_Forearm')]:
        bone=eb[side+'_'+name];bone.head=a;bone.tail=b;bone.parent=eb[parent];bone.use_connect=False;bone.align_roll(Vector((0,0,1)))
    for short in ['Upperarm','Forearm']:
        helper=eb[side+'_'+short+'Twist02'];helper.parent=eb[side+'_'+short]
    # Approximate MMD neutral arm directions; recalibrate for the intended motion rig.
    uref=Vector((sign*math.cos(math.radians(31)),0,-math.sin(math.radians(31))))
    fref=Vector((sign*math.cos(math.radians(40)),0,-math.sin(math.radians(40))))
    qu=(el-sh).normalized().rotation_difference(uref);qf=(wr-el).normalized().rotation_difference(fref)
    arm_calibration[side]=(qu.copy(),qf.copy())
    hand_points={};finger_names={}
    for eng,prefix,tip in finger_defs:
        # Fit the phalanges inside this character's original high-resolution fingers.
        original_points={
            'Thumb':[(.652,-.034,1.248),(.677,-.051,1.241),(.701,-.069,1.242),(.718,-.080,1.240)],
            'Index':[(.699,-.024,1.253),(.735,-.026,1.258),(.759,-.027,1.262),(.777,-.027,1.262)],
            'Middle':[(.706,-.004,1.255),(.746,-.004,1.261),(.770,-.004,1.263),(.787,-.004,1.264)],
            'Ring':[(.704,.014,1.255),(.738,.016,1.260),(.759,.018,1.263),(.776,.019,1.264)],
            'Pinky':[(.697,.029,1.250),(.722,.034,1.252),(.739,.038,1.254),(.754,.040,1.258)]}
        points=[Vector((sign*x,y,z)) for x,y,z in original_points[eng]]
        ids=[0,1,2] if eng=='Thumb' else [1,2,3]
        names=[]
        for j,i in enumerate(ids):
            name=f'{side}_{eng}_{i}';bone=eb.new(name);bone.head=points[j];bone.tail=points[j+1]
            bone.parent=eb[names[-1]] if names else eb[side+'_Hand'];bone.use_connect=bool(names);bone.align_roll(Vector((0,0,1)))
            names.append(name);mapping[jp+prefix+'０１２３'[i]]=name
        hand_points[eng]=points;finger_names[eng]=names
    eb[side+'_Hand'].head=wr;eb[side+'_Hand'].tail=hand_points['Middle'][0];eb[side+'_Hand'].parent=eb[side+'_ForearmTwist01'];eb[side+'_Hand'].use_connect=False
    hands[side]={'wrist':wr,'points':hand_points,'names':finger_names}
bpy.ops.object.mode_set(mode='OBJECT')
fcol=arm.data.collections.new('Fingers / 手指')
for info in hands.values():
    for names in info['names'].values():
        for name in names:fcol.assign(arm.data.bones[name]);arm.data.bones[name].color.palette='THEME05'

# Repaint the sleeves around the actual shoulder, elbow, and wrist pivots.
for v in body.data.vertices:
    x,y,z=v.co;t=abs(x)
    if not (.17<t and 1.025<z<1.44):continue
    side='L' if x>0 else 'R';mix=smooth(.17,.24,t)
    old={g.group:g.weight for g in v.groups}
    arm_weight=sum(w for i,w in old.items() if body.vertex_groups[i].name.startswith(side+'_') and any(part in body.vertex_groups[i].name for part in ['Clavicle','Upperarm','Forearm','Hand']))
    mix*=smooth(.12,.6,arm_weight)
    if mix<1e-5:continue
    fore=smooth(.365,.442,t);hand=smooth(.606,.647,t)
    ut=.85*smooth(.235,.39,t);ft=.9*smooth(.442,.625,t)
    weights={'Upperarm':(1-fore)*(1-ut),'UpperarmTwist01':(1-fore)*ut,
             'Forearm':fore*(1-hand)*(1-ft),'ForearmTwist01':fore*(1-hand)*ft,'Hand':fore*hand}
    target={body.vertex_groups[side+'_'+n].index:w for n,w in weights.items()}
    for idx in set(old)|set(target):body.vertex_groups[idx].add([v.index],old.get(idx,0)*(1-mix)+target.get(idx,0)*mix,'REPLACE')

# Bind the existing fingers directly. No hand faces are removed or replaced.
for side,info in hands.items():
    sign=1 if side=='L' else -1
    for names in info['names'].values():
        for name in names:
            if not body.vertex_groups.get(name):body.vertex_groups.new(name=name)
    for vert in body.data.vertices:
        if sign*vert.co.x<.636:continue
        # Cuff ornaments stay with the wrist instead of being treated as finger skin.
        is_skin=sign*vert.co.x>.667 or (sign*vert.co.x>.645 and vert.co.z<1.275 and vert.co.y<-.035)
        if not is_skin:continue
        closest=None
        for finger,ps in info['points'].items():
            root=(vert.co-ps[0]).dot((ps[1]-ps[0]).normalized())
            if root<-.010:continue
            for j in range(3):
                d=ps[j+1]-ps[j];t=max(0,min(1,(vert.co-ps[j]).dot(d)/d.length_squared))
                dist=(vert.co-(ps[j]+t*d)).length
                if closest is None or dist<closest[0]:closest=(dist,finger,j,t,root)
        weights={side+'_Hand':1.0}
        if closest:
            dist,finger,j,t,root=closest;ps=info['points'][finger];names=info['names'][finger]
            if dist<(.016 if finger=='Thumb' else .014):
                amount=smooth(-.005,.015,root) if j==0 else 1.0
                weights={side+'_Hand':1-amount,names[j]:amount}
                lengths=[(ps[k+1]-ps[k]).length for k in range(3)];along=sum(lengths[:j])+t*lengths[j]
                for joint in [1,2]:
                    d=along-sum(lengths[:joint])
                    if abs(d)<.005:
                        blend=smooth(-.005,.005,d);weights={names[joint-1]:1-blend,names[joint]:blend};break
        wrist_blend=smooth(.628,.660,sign*vert.co.x)
        weights={k:w*wrist_blend for k,w in weights.items()};weights[side+'_ForearmTwist01']=1-wrist_blend
        for w in list(vert.groups):body.vertex_groups[w.group].remove([vert.index])
        for name,w in weights.items():
            if w>.000001:body.vertex_groups[name].add([vert.index],w,'REPLACE')
    print('ORIGINAL_HAND_BOUND',side,flush=True)

# Smooth only weights across neighboring hand vertices; keep all coordinates and UVs unchanged.
mesh=body.data;allco=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',allco);allco=allco.reshape(-1,3)
edges=np.empty(len(mesh.edges)*2,np.int32);mesh.edges.foreach_get('vertices',edges);edges=edges.reshape(-1,2)
for side,sign in [('L',1),('R',-1)]:
    used=np.flatnonzero(allco[:,0]*sign>.630);lookup=np.full(len(allco),-1,np.int32);lookup[used]=np.arange(len(used))
    unique,inv=np.unique(np.round(allco[used],6),axis=0,return_inverse=True)
    hand_names=[g.name for g in body.vertex_groups if g.name.startswith(side+'_') and any(k in g.name for k in ['Hand','Forearm','Thumb','Index','Middle','Ring','Pinky'])]
    gids=[body.vertex_groups[n].index for n in hand_names];cols={g:i for i,g in enumerate(gids)}
    w=np.zeros((len(unique),len(gids)));ct=np.bincount(inv,minlength=len(unique))
    for j,idx in enumerate(used):
        for vg in mesh.vertices[int(idx)].groups:
            if vg.group in cols:w[inv[j],cols[vg.group]]+=vg.weight
    w/=ct[:,None]
    ee=edges[(lookup[edges]>=0).all(axis=1)];ee=inv[lookup[ee]];ee=np.unique(np.sort(ee,axis=1),axis=0);ee=ee[ee[:,0]!=ee[:,1]]
    degree=np.bincount(ee.ravel(),minlength=len(unique))
    for _ in range(20):
        acc=np.zeros_like(w);np.add.at(acc,ee[:,0],w[ee[:,1]]);np.add.at(acc,ee[:,1],w[ee[:,0]])
        w=.40*w+.60*acc/np.maximum(degree,1)[:,None]
    w/=np.maximum(w.sum(1),1e-10)[:,None]
    for j,idx in enumerate(used):
        vert=mesh.vertices[int(idx)]
        for vg in list(vert.groups):body.vertex_groups[vg.group].remove([int(idx)])
        for gi,amount in zip(gids,w[inv[j]]):
            if amount>.000001:body.vertex_groups[gi].add([int(idx)],float(amount),'REPLACE')
    print('HAND_WEIGHTS_SMOOTHED',side,flush=True)

# Calibrate the character's neutral arms to the MMD reference before importing relative rotations.
arm.data.pose_position='POSE'
for side,(qu,qf) in arm_calibration.items():
    pb=arm.pose.bones[side+'_Upperarm'];rest=pb.bone.matrix_local
    pb.matrix=Matrix.Translation(rest.translation)@qu.to_matrix().to_4x4()@rest.to_3x3().to_4x4();bpy.context.view_layer.update()
    pb=arm.pose.bones[side+'_Forearm'];pos=pb.head.copy();rest=pb.bone.matrix_local
    pb.matrix=Matrix.Translation(pos)@qf.to_matrix().to_4x4()@rest.to_3x3().to_4x4();bpy.context.view_layer.update()
for ob in meshes:
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    for mod in list(ob.modifiers):
        if mod.type=='ARMATURE':bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.armature_apply(selected=False);bpy.ops.object.mode_set(mode='OBJECT')
for ob in meshes:
    mod=ob.modifiers.new('Character deformation','ARMATURE');mod.object=arm;mod.use_deform_preserve_volume=True
for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)

# Anatomical one-axis knees replace the unstable pole controls.
hinges={}
def ik(owner,target,count):
    c=arm.pose.bones[owner].constraints.new('IK');c.name='MMD '+target;c.target=arm;c.subtarget=target;c.chain_count=count;c.iterations=160;c.use_stretch=False
    ctrl=arm.pose.bones[target];ctrl['IK_enabled']=1.0
    d=c.driver_add('influence').driver;d.type='SCRIPTED';d.expression='enabled'
    v=d.variables.new();v.name='enabled';v.type='SINGLE_PROP';v.targets[0].id=arm;v.targets[0].data_path=f'pose.bones["{target}"]["IK_enabled"]'
for side in ['L','R']:
    thigh=arm.data.bones[side+'_Thigh'];calf=arm.data.bones[side+'_Calf'];a=(thigh.tail_local-thigh.head_local).normalized();b=(calf.tail_local-calf.head_local).normalized()
    axis=calf.matrix_local.to_3x3().col[0];rest_angle=math.atan2(axis.dot(a.cross(b)),a.dot(b))
    pb=arm.pose.bones[side+'_Calf'];pb.lock_ik_y=True;pb.lock_ik_z=True;pb.use_ik_limit_x=True;pb.ik_min_x=-rest_angle+.003;pb.ik_max_x=math.radians(150)-rest_angle
    ik(side+'_Calf',side+'_Foot_IK',2);ik(side+'_Foot',side+'_Toe_IK',1)
    pb.rotation_quaternion=Quaternion((1,0,0),math.radians(25));pb['cosmmd_preferred_bend_degrees']=25.0
    hinges[side]={'rest_angle_degrees':math.degrees(rest_angle),'min':pb.ik_min_x,'max':pb.ik_max_x}
for jp,name in mapping.items():arm.pose.bones[name]['MMD_name']=jp
arm['mmd_mapping_json']=json.dumps(mapping,ensure_ascii=False);arm['rig_revision']='v3: preserved original high-resolution hands, shoes and socks; local inner-leg separation; fitted finger bones; anatomical IK and calibrated arm pose.'
(ROOT/'work/mmd_mapping_v3.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2))
(ROOT/'work/v3_hinges.json').write_text(json.dumps(hinges,indent=2))
s.frame_start=1;s.frame_end=1;s.frame_set(1)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'work/Calibrated_Rig.blend'))
