# Reference-character calibration recipe: fitted to the showcase anatomy, not a universal preset.
import os
import bpy,bmesh,sys,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(os.environ['COSMMD_RUN']).resolve()
sys.path.insert(0,str(Path(__file__).parent))
from scene_common import aim_camera
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/MMD_Prepared.blend'))
s=bpy.context.scene;arm=bpy.data.objects['Rig'];old=bpy.data.objects['Character']
arm.animation_data_clear();arm.data.pose_position='REST'
for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for mod in old.modifiers:mod.show_viewport=False;mod.show_render=False
with bpy.data.libraries.load(str(ROOT/'source/Source_High.blend'),link=False) as (src,dst):dst.objects=['Source_High']
source=dst.objects[0];s.collection.objects.link(source);source.data.transform(Matrix.Scale(1.65/.978759765625,4));source.matrix_world=Matrix.Identity(4)
for mod in list(source.modifiers):source.modifiers.remove(mod)
for g in list(source.vertex_groups):source.vertex_groups.remove(g)
for g in old.vertex_groups:source.vertex_groups.new(name=g.name)
bpy.ops.object.select_all(action='DESELECT');source.select_set(True);bpy.context.view_layer.objects.active=source
transfer=source.modifiers.new('Original surface rig weights','DATA_TRANSFER');transfer.object=old
transfer.use_vert_data=True;transfer.data_types_verts={'VGROUP_WEIGHTS'};transfer.vert_mapping='POLYINTERP_NEAREST';transfer.layers_vgroup_select_src='ALL';transfer.layers_vgroup_select_dst='NAME'
bpy.ops.object.modifier_apply(modifier=transfer.name)
print('WEIGHTS_TRANSFERRED',flush=True)
# Split the existing faces at the hem height without changing their surface or UVs.
bm=bmesh.new();bm.from_mesh(source.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.0000001,plane_co=(0,0,.680),plane_no=(0,0,1))
bm.to_mesh(source.data);bm.free()
me=source.data;co=np.empty(len(me.vertices)*3);me.vertices.foreach_get('co',co);co=co.reshape(-1,3)
starts=np.empty(len(me.polygons),np.int32);counts=np.empty(len(me.polygons),np.int32);indices=np.empty(len(me.loops),np.int32)
me.polygons.foreach_get('loop_start',starts);me.polygons.foreach_get('loop_total',counts);me.loops.foreach_get('vertex_index',indices)
centers=np.add.reduceat(co[indices],starts)/counts[:,None];x,y,z=centers.T
leg_ids={g.index for g in source.vertex_groups if g.name.startswith(('L_','R_')) and any(k in g.name for k in ['Thigh','Calf','Foot','ToeBase'])}
leg_weight=np.array([sum(g.weight for g in v.groups if g.group in leg_ids) for v in me.vertices])
face_leg_weight=np.add.reduceat(leg_weight[indices],starts)/counts
leg=(z<.680001)&(abs(x)<.16)&(y>np.where(z<.45,-.145,-.115))&(y<.115)
def extract(name,chosen):
 li=np.concatenate([np.arange(starts[p],starts[p]+counts[p]) for p in chosen]);used=np.unique(indices[li]);lookup=np.full(len(co),-1,np.int32);lookup[used]=np.arange(len(used))
 faces=[lookup[indices[starts[p]:starts[p]+counts[p]]].tolist() for p in chosen]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(co[used].tolist(),[],faces);mesh.update()
 for mat in me.materials:mesh.materials.append(mat)
 for a,b in zip(mesh.polygons,chosen):a.material_index=me.polygons[b].material_index;a.use_smooth=True
 for uv in me.uv_layers:
  data=np.empty(len(me.loops)*2,np.float32);uv.data.foreach_get('uv',data);layer=mesh.uv_layers.new(name=uv.name);layer.data.foreach_set('uv',data.reshape(-1,2)[li].ravel())
 obj=bpy.data.objects.new(name,mesh);s.collection.objects.link(obj);obj.parent=arm
 for g in source.vertex_groups:obj.vertex_groups.new(name=g.name)
 for j,i in enumerate(used):
  for w in me.vertices[int(i)].groups:
   if w.weight>.0001:obj.vertex_groups[w.group].add([j],w.weight,'REPLACE')
 return obj
body=extract('Source_Body',np.flatnonzero(~leg));legs=extract('Source_Leg_Surface',np.flatnonzero(leg))
# Clothing remaining above the hem must not be pulled by the thigh or calf bones.
for v in body.data.vertices:
 if v.co.z>.97:continue
 old_weights={g.group:g.weight for g in v.groups};amount=sum(w for g,w in old_weights.items() if g in leg_ids)
 if amount<.00001:continue
 for idx in leg_ids:
  if idx in old_weights:body.vertex_groups[idx].remove([v.index])
 existing_skirt={g:w for g,w in old_weights.items() if body.vertex_groups[g].name.startswith('Skirt_')}
 total=sum(existing_skirt.values())
 if total>.05:
  for g,w in existing_skirt.items():body.vertex_groups[g].add([v.index],w+amount*w/total,'REPLACE')
 else:
  idx=body.vertex_groups['Pelvis'].index;body.vertex_groups[idx].add([v.index],old_weights.get(idx,0)+amount,'REPLACE')
print('SURFACES_EXTRACTED',len(body.data.vertices),len(legs.data.vertices),flush=True)
# A separate material is used only on newly exposed interior seams.
capmat=bpy.data.materials.new('Inner leg seam only');capmat.use_nodes=True
bs=capmat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.78
cn=capmat.node_tree.nodes.new('ShaderNodeVertexColor');cn.layer_name='RepairColor';capmat.node_tree.links.new(cn.outputs['Color'],bs.inputs['Base Color'])
img=bpy.data.images.load(str(ROOT/'work/basecolor_sample.png'),check_existing=True);pix=np.array(img.pixels[:]).reshape(img.size[1],img.size[0],4)
def color(uv):
 rgba=pix[int((uv.y%1)*(img.size[1]-1)),int((uv.x%1)*(img.size[0]-1))].copy();rgb=rgba[:3];rgba[:3]=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);rgba[3]=1;return rgba.tolist()
def smooth(a,b,x):
 t=min(1,max(0,(x-a)/(b-a)));return t*t*(3-2*t)
parts=[body];report={}
for side,sign in [('L',1),('R',-1)]:
 ob=legs.copy();ob.data=legs.data.copy();ob.name='Leg_'+side;s.collection.objects.link(ob);ob.data.materials.append(capmat);capindex=len(ob.data.materials)-1
 bm=bmesh.new();bm.from_mesh(ob.data)
 # Exact UV duplicates are welded without moving the outer surface.
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000005)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.0000001,plane_co=(.008,0,0),plane_no=(-sign,0,sign*.020833333),clear_outer=True)
 uv=bm.loops.layers.uv.active;cl=bm.loops.layers.float_color.new('RepairColor')
 vuv={v:next(iter(v.link_loops))[uv].uv.copy() for v in bm.verts if v.link_loops}
 caps=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0).get('faces',[])
 for f in caps:
  f.material_index=capindex;f.smooth=True
  for l in f.loops:l[uv].uv=vuv[l.vert];l[cl]=color(vuv[l.vert])
 # The generated character has no complete upper thigh beneath its skirt.
 # Extend only the newly exposed horizontal closure inside the garment.
 top=[f for f in caps if all(abs(v.co.z-.680)<.00001 for v in f.verts)]
 for step in range(8):
  if not top:break
  ex=bmesh.ops.extrude_face_region(bm,geom=top,use_keep_orig=False)
  newverts=[v for v in ex['geom'] if isinstance(v,bmesh.types.BMVert)]
  for v in newverts:
   v.co.z+=.0275;v.co.x+=sign*.0035;v.co.y-=.003
  top=[f for f in ex['geom'] if isinstance(f,bmesh.types.BMFace) and all(v in newverts for v in f.verts)]
  for f in ex['geom']:
   if isinstance(f,bmesh.types.BMFace):f.material_index=capindex;f.smooth=True
 caps=[f for f in bm.faces if f.material_index==capindex]
 bmesh.ops.triangulate(bm,faces=caps)
 # Subdivide only new cap faces at short height intervals for knee deformation.
 for zz in np.arange(.015,.88,.02):
  fs=[f for f in bm.faces if f.material_index==capindex];es={e for f in fs for e in f.edges};vs={v for f in fs for v in f.verts}
  bmesh.ops.bisect_plane(bm,geom=list(vs)+list(es)+fs,dist=.0000001,plane_co=(0,0,float(zz)),plane_no=(0,0,1))
 for yy in np.arange(-.15,.14,.012):
  fs=[f for f in bm.faces if f.material_index==capindex];es={e for f in fs for e in f.edges};vs={v for f in fs for v in f.verts}
  bmesh.ops.bisect_plane(bm,geom=list(vs)+list(es)+fs,dist=.0000001,plane_co=(0,float(yy),0),plane_no=(0,1,0))
 boundary=[v for v in bm.verts if any(f.material_index==capindex for f in v.link_faces) and any(f.material_index!=capindex for f in v.link_faces)]
 boundary_co=np.array([list(v.co) for v in boundary])
 # Round only the newly exposed interior; every original outer-surface vertex stays fixed.
 for v in bm.verts:
  if not v.link_faces or any(f.material_index!=capindex for f in v.link_faces):continue
  near=boundary_co[abs(boundary_co[:,2]-v.co.z)<.018]
  if len(near)<2:continue
  low=float(near[:,1].min());high=float(near[:,1].max())
  if high-low<.02:continue
  t=min(1,max(0,(v.co.y-low)/(high-low)));amount=(.008 if v.co.z<.12 else .016)*math.sin(math.pi*t)
  v.co.x-=sign*amount*smooth(.0,.03,v.co.z)*(1-smooth(.82,.90,v.co.z))
 bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if f.material_index==capindex]);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for f in bm.faces:
  if f.material_index==capindex:f.smooth=True
 deform=bm.verts.layers.deform.active;ids={p:ob.vertex_groups[side+'_'+p].index for p in ['Thigh','Calf','Foot']}
 for v in bm.verts:
  w=v[deform];w.clear();th=smooth(.42,.54,v.co.z);ft=1-smooth(.095,.17,v.co.z)
  for part,amount in [('Thigh',th),('Calf',(1-th)*(1-ft)),('Foot',(1-th)*ft)]:
   if amount>.000001:w[ids[part]]=amount
 report[side]={'vertices':len(bm.verts),'new_interior_faces':sum(f.material_index==capindex for f in bm.faces),'outer_surface_moved':False}
 bm.to_mesh(ob.data);bm.free();parts.append(ob);print('LEG_SEPARATED',side,report[side],flush=True)
for ob in [old,source,legs]:bpy.data.objects.remove(ob,do_unlink=True)
body.name='Character'
for ob in parts:
 mod=ob.modifiers.new('Character deformation','ARMATURE');mod.object=arm;mod.use_deform_preserve_volume=True
 ob['source_preservation']='Original high-resolution surface and UVs retained. Only hidden joined leg interior was cut and capped.'
s.frame_set(1);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'work/Source_T.blend'))
(ROOT/'work/source_preservation_v3.json').write_text(json.dumps(report,indent=2))
print('SOURCE_RESTORED',flush=True)
