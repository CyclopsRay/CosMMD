import bpy
from mathutils import Vector

def material(name, color, roughness=0.65):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1)
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=roughness
    return m

def setup_stage(height=1.0):
    scene=bpy.context.scene
    scene.render.engine='CYCLES'; scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1000; scene.render.resolution_y=1000
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.fps=30
    scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('Warm Studio'); world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(0.24,0.23,0.25,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=0.5
    scene.world=world
    bpy.ops.object.camera_add(location=(0,-2.8*height,.58*height))
    cam=bpy.context.object; cam.name='Camera_Front'
    aim_camera(cam,(0,0,.51*height))
    cam.data.type='ORTHO'; cam.data.ortho_scale=1.25*height; scene.camera=cam
    for name,loc,power,size in [
        ('Key_Softbox',(-1.1,-1.5,1.9),100,1.1),
        ('Fill_Softbox',(1.1,-.8,1.2),65,.9),
        ('Rim_Softbox',(.6,.9,1.8),125,.9)]:
        bpy.ops.object.light_add(type='AREA',location=tuple(x*height for x in loc))
        ob=bpy.context.object; ob.name=name; ob.data.energy=power*height*height
        ob.data.shape='DISK'; ob.data.size=size*height
        aim_camera(ob,(0,0,.6*height))
    bpy.ops.mesh.primitive_plane_add(size=200*height,location=(0,0,-.005*height))
    floor=bpy.context.object; floor.name='Studio_Floor'
    floor.data.materials.append(material('Backdrop',(.18,.14,.155)))
    return cam

def aim_camera(cam,target):
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
