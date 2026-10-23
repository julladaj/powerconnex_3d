"""Rebuild the reference-based Power Connex asset in Blender. Units authored in mm."""
import bpy, math, json, os
from mathutils import Vector
from math import sin, cos, pi
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'output')
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    if collection.name != 'Collection':
        bpy.data.collections.remove(collection)
bpy.data.orphans_purge(do_recursive=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'MILLIMETERS'
scene.unit_settings.scale_length = 1

def material(name, color, metal=0, rough=.4):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    m.diffuse_color = (*color, 1)
    return m
black = material('Black_Molded_Polymer', (.008,.009,.010), 0, .4)
next(n for n in black.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Specular IOR Level'].default_value=.28
shuttermat = material('Safety_Shutter_Polymer', (.031,.034,.033), 0, .43)
gold = material('Gold_Anodized_Aluminum', (.53,.345,.035), .72, .32)
copper = material('Solid_Copper', (.63,.25,.085), .88, .25)
nickel = material('Copper_Coated_Nickel_Contact', (.48,.44,.34), .85, .27)
steel = material('Industrial_Spring_Steel', (.42,.46,.49), .9, .25)
solder = material('Lead_Free_Solder', (.55,.58,.58), .85, .32)
pvc = material('Black_PVC_Insulation', (.009,.011,.012), 0, .54)
ink = material('Recessed_Marking_Ink', (.007,.008,.008), 0, .63)

product = bpy.data.collections.new('PRODUCT'); scene.collection.children.link(product)
studio = bpy.data.collections.new('STUDIO'); scene.collection.children.link(studio)
refs = bpy.data.collections.new('REFERENCE_IMAGES'); scene.collection.children.link(refs)
refs.hide_render = True; refs.hide_viewport = True
def move_coll(o, coll):
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o)
def empty(name, parent=None):
    o=bpy.data.objects.new(name,None); product.objects.link(o); o.parent=parent
    o.empty_display_size=.005; return o
root = empty('PowerConnex_PowerStrip')
root['description']='Four-outlet reference reconstruction; default exploded pose from Description-3.jpg'
root['scale_note']='Estimated: housing length 300 mm. Not measured or manufacturing geometry.'
root['source_images']='Description-1.jpg; Description-2.jpg; Description-3.jpg'
root['assembled_housing_dimensions_mm']=[300,65,42]
root['pose']='exploded'
root['assembly_version']=2
chassis = empty('Housing_And_Mounting',root)
electrical = empty('Conductors_And_Insulation',root)

def finish(o,name,mat,parent,assembled=None):
    o.name=name; move_coll(o,product); o.parent=parent
    if mat: o.data.materials.append(mat)
    if assembled is not None: o['assembled_location_m']=[v*.001 for v in assembled]
    o['exploded_location_m']=list(o.location)
    return o
def box(name, dims, pos, mat=black, parent=chassis, bevel=.35, assembled=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[v*.001 for v in pos])
    o=bpy.context.object; o.dimensions=[v*.001 for v in dims]
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    finish(o,name,mat,parent,assembled)
    if bevel: edge(o,bevel)
    return o
def edge(o,width=.3,segments=2):
    m=o.modifiers.new('Edge_Radius','BEVEL'); m.width=width*.001; m.segments=segments
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_apply(modifier=m.name)
    return o
def cyl(name,r,depth,pos,mat=black,parent=chassis,axis='Z',verts=24,assembled=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r*.001,depth=depth*.001,location=[v*.001 for v in pos])
    o=bpy.context.object
    if axis=='X': o.rotation_euler[1]=pi/2
    if axis=='Y': o.rotation_euler[0]=pi/2
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    return finish(o,name,mat,parent,assembled)
def cut(o,tool):
    bpy.context.view_layer.objects.active=o
    m=o.modifiers.new('Aperture','BOOLEAN'); m.operation='DIFFERENCE'; m.solver='EXACT'; m.object=tool
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool,do_unlink=True)
def join(parts,name):
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.join()
    o=parts[0]; o.name=name
    return o
def origin_at(o, pos):
    # Rebase only this object, preserving its world geometry and other pivots.
    old = o.matrix_world.copy()
    rebased = old.copy(); rebased.translation = Vector(pos) * .001
    if o.data.users > 1: o.data = o.data.copy()
    o.data.transform(rebased.inverted() @ old)
    o.matrix_world = rebased
    o['exploded_location_m']=list(o.location)
def smooth(o):
    for f in o.data.polygons: f.use_smooth=True
def tube(name, points, radius, mat, parent, sides=8):
    curve=bpy.data.curves.new(name,'CURVE'); curve.dimensions='3D'; curve.resolution_u=1
    curve.bevel_depth=radius*.001; curve.bevel_resolution=1
    curve.resolution_u=1
    s=curve.splines.new('POLY'); s.points.add(len(points)-1)
    for p,co in zip(s.points,points): p.co=(*[v*.001 for v in co],1)
    o=bpy.data.objects.new(name,curve); product.objects.link(o); o.parent=parent; curve.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o.select_set(False)
    smooth(o); return o

# One extruded U-shaped aluminum shell, including longitudinal internal retaining lips.
shellparts=[box('Aluminum_Alloy_Housing',(300,65,2),(0,0,1),gold,assembled=(0,0,1)),
    box('wall',(300,2,40),(0,-31.5,22),gold),box('wall',(300,2,40),(0,31.5,22),gold)]
for y in [-28.8,28.8]:
    shellparts.append(box('Retaining_Lip',(300,.5,2),(0,math.copysign(30.25,y),33),gold,bevel=.1))
    shellparts.append(box('Inner_Guide',(300,2,2),(0,y,13),gold,bevel=.2))
shell=join(shellparts,'Aluminum_Alloy_Housing'); origin_at(shell,(0,0,0)); shell['assembled_location_m']=[0,0,0]
shell['reference_label']='ALUMINUM ALLOY / STRUCTERED CASE'
shell['construction_note']='Single U-channel extrusion; golden anodized finish inferred from images.'
for side,s in [('Left',-1),('Right',1)]:
    x=s*178
    cap=box('End_Plate_'+side,(2.6,65,43),(x,0,21.5),black,assembled=(s*151.3,0,21.5))
    if side=='Left': cut(cap,cyl('tool',9.5,6,(x,0,20),axis='X',verts=40))
    for y in [-24,24]:
        for z in [8,35]: cut(cap,cyl('tool',1.7,7,(x,y,z),axis='X',verts=16))
    # Mounting angle: slotted base plate, upright profile and large open cable/mounting relief.
    bx=s*218
    foot=box('Mounting_Bracket_'+side,(30,70,2.5),(bx+s*13,0,1.25),black,assembled=(s*167,0,1.25))
    upright=box('Upright',(2.5,70,52),(bx,0,27),black)
    cut(upright,cyl('Relief',20,7,(bx,0,38),axis='X',verts=40))
    cut(upright,box('Open_Top',(8,36,23),(bx,0,52),bevel=0))
    for y in [-27,27]:
        cut(upright,cyl('Fixing_Hole',2,7,(bx,y,44),axis='X',verts=20))
        cut(upright,cyl('Fixing_Hole',2,7,(bx,y,17),axis='X',verts=20))
    for y in [-24,0,24]:
        tool=box('Slot',(15,7,7),(bx+s*15,y,1),bevel=3.4)
        cut(foot,tool)
    bracket=join([foot,upright],'Mounting_Bracket_'+side)
    origin_at(bracket,(bx,0,0)); bracket['assembled_location_m']=[s*.153,0,0]
    bracket['reference_label']='4 STYLES HANGING: removable mounting bracket'
    box('Top_End_Cover_'+side,(10,65,3),(s*145,0,60),black,
        bevel=.15,assembled=(s*145,0,43.5))

# Insulation liner and three continuous copper conductor strips.
liner=box('PVC_Insulation_Liner',(290,55,1.8),(0,0,48),pvc,electrical,assembled=(0,0,8))
for y in [-26,26]:
    rail=box('PVC_Insulation_Retainer_'+('Front' if y<0 else 'Back'),(290,2,7),(0,y,51),pvc,electrical,assembled=(0,y,11))
for i,y in enumerate([-18,0,18],1):
    bus=box('Solid_Copper_Bar_%02d'%i,(284,3,3),(0,y,62),copper,electrical,bevel=.4,assembled=(0,y,14))
    bus['reference_label']='SOLID COPPER BAR'
    bus['inference_note']='Three longitudinal conductors inferred from outlet function; hidden routing not specified by images.'

# Logo sampled from the supplied artwork, used only on the product faceplates.
src=bpy.data.images.load(os.path.join(ROOT,'Description-2.jpg'),check_existing=True)
w,h=src.size; pix=np.array(src.pixels[:],dtype=np.float32).reshape(h,w,4)
crop=pix[h-72:h-37,902:1003,:3]
alpha=np.clip((.32-crop.mean(axis=2))/.22,0,1)
rgba=np.zeros((*alpha.shape,4),dtype=np.float32); rgba[:,:,:3]=.008; rgba[:,:,3]=alpha
logo=bpy.data.images.new('PowerConnex_Reference_Logo',width=rgba.shape[1],height=rgba.shape[0],alpha=True)
logo.pixels.foreach_set(rgba.ravel()); logo.filepath_raw=os.path.join(OUT,'powerconnex_logo.png'); logo.file_format='PNG'; logo.save(); logo.pack()
logomat=material('PowerConnex_Logo_Decal',(.006,.006,.006),0,.5)
nodes=logomat.node_tree.nodes; p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
t=nodes.new('ShaderNodeTexImage'); t.image=logo
logomat.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color']); logomat.node_tree.links.new(t.outputs['Alpha'],p.inputs['Alpha'])
try: logomat.surface_render_method='DITHERED'
except Exception: pass
def decal(name,x,y,z,parent):
    verts=[((x-11)*.001,(y-3.8)*.001,z*.001),((x+11)*.001,(y-3.8)*.001,z*.001),((x+11)*.001,(y+3.8)*.001,z*.001),((x-11)*.001,(y+3.8)*.001,z*.001)]
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],[(0,1,2,3)]); me.uv_layers.new()
    for loop,uv in zip(me.uv_layers.active.data,[(0,0),(1,0),(1,1),(0,1)]): loop.uv=uv
    o=bpy.data.objects.new(name,me); product.objects.link(o); o.parent=parent; me.materials.append(logomat)
    origin_at(o,(x,y,z))
    return o
def label(name,text,pos,size,parent):
    cu=bpy.data.curves.new(name,'FONT'); cu.body=text; cu.size=size*.001; cu.align_x='CENTER'; cu.extrude=0; cu.resolution_u=2
    o=bpy.data.objects.new(name,cu); product.objects.link(o); o.parent=parent; o.location=[v*.001 for v in pos]; cu.materials.append(ink)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o; bpy.ops.object.convert(target='MESH')
    o['exploded_location_m']=list(o.location)
    return o

for idx,x in enumerate([-105,-35,35,105],1):
    pre='Outlet_%02d_'%idx; group=empty('Outlet_%02d'%idx,root)
    # Open, ribbed molded lower socket body.
    bodyparts=[box(pre+'Molded_Outlet_Body',(57,59,5),(x,0,76),black,group,assembled=(x,0,20.4))]
    for yy in [-18,0,18]:
        cut(bodyparts[0],box('Terminal_Clearance',(12,8*63/60,10),(x,yy*63/60,76),bevel=.3))
    for y in [-27.5,27.5]:
        wall=box('Body_Wall',(57,4,19.6),(x,y,85.8),black,group)
        for dx in [-19,-10,10,19]:
            cut(wall,box('Latch_Notch',(3.5,8,10),(x+dx,y,96),bevel=.25))
        bodyparts.append(wall)
    for xx in [-26.5,26.5]: bodyparts.append(box('Body_End',(4,51,19.6),(x+xx,0,85.8),black,group))
    for yy in [-12,12]: bodyparts.append(box('Internal_Partition',(49,2,6.6),(x,yy,81.8),black,group,bevel=.2))
    for dx in [-19,19]:
        for yy in [-19,19]: bodyparts.append(box('Lower_Mounting_Leg',(7,8,9),(x+dx,yy,69),black,group,bevel=.35))
    for xx in [-19,-9,9,19]:
        for yy in [-30,30]: bodyparts.append(box('Reinforcing_Rib',(1.8,3,13),(x+xx,yy,87),black,group,bevel=.18))
    body=join(bodyparts,pre+'Molded_Outlet_Body'); origin_at(body,(x,0,76)); body['assembled_location_m']=[x*.001,0,.0204]
    for vertex in body.data.vertices: vertex.co.y *= 60/63
    body['reference_label']='MOLDED OUTLET / KNITTED STRUCTURE'
    for ci,yy in enumerate([-18,0,18],1):
        # Individually removable folded metal clips and solder joints.
        bits=[box('Contact_Sole',(9,6,1),(x,yy,70),nickel,group,bevel=.15),box('Contact_Terminal',(3,3,7),(x,yy,66),nickel,group,bevel=.2)]
        for xx in [-3.5,3.5]: bits.append(box('Contact_Jaw',(1,6,12),(x+xx,yy,75),nickel,group,bevel=.25))
        contact=join(bits,pre+'Copper_Coated_Nickel_Contact_%02d'%ci); origin_at(contact,(x,yy,70)); contact['assembled_location_m']=[x*.001,yy*.001,.022]
        ball=cyl(pre+'Lead_Free_Solder_%02d'%ci,2,2,(x,yy,64),solder,group,verts=16,assembled=(x,yy,16)); edge(ball,.6); smooth(ball)
    # Layer above body: carrier with side walls, separated from both spring and shutter.
    cp=[box(pre+'Shutter_Carrier',(48,47,3),(x,0,105),black,group,assembled=(x,0,31))]
    for yy in [-18,0,18]:
        cut(cp[0],box('Carrier_Pin_Clearance',(12,8,8),(x,yy,105),bevel=.5))
    for xx in [-22,22]: cp.append(box('Carrier_End',(4,47,11),(x+xx,0,110),black,group))
    for yy in [-22.75,22.75]: cp.append(box('Carrier_Rail',(40,1.5,6),(x,yy,107),black,group))
    carrier=join(cp,pre+'Shutter_Carrier'); origin_at(carrier,(x,0,105)); carrier['assembled_location_m']=[x*.001,0,.031]
    # Closely wound cylindrical steel compression spring with a horizontal axis.
    pts=[]; turns=16; count=turns*14
    for k in range(count+1):
        a=2*pi*turns*k/count
        pts.append((x-13+26*k/count,10+3.5*cos(a),119+3.5*sin(a)))
    spring=tube(pre+'Industrial_Spring',pts,.48,steel,group)
    origin_at(spring,(x,10,119)); spring['assembled_location_m']=[x*.001,.013,.0365]
    spring['reference_label']='INDUSTRIAL SPRING'
    shutter=box(pre+'Safety_Shutter',(35,21,4),(x,-2,133),shuttermat,group,bevel=.5,assembled=(x,-2,38.5))
    for dx in [-10,10]:
        # Ramp-like bevelled openings in the sliding safety plate.
        cut(shutter,box('Shutter_Opening',(5,8,8),(x+dx,-4,133),bevel=.4))
    shutter['reference_label']='SAFTY SHUTTER'
    # Top plate. The three universal apertures are real cutouts, not painted circles.
    face=box(pre+'Faceplate',(70,65,3),(x,0,151),black,group,bevel=.2,assembled=(x,0,43.5))
    for dx,yy in [(-14,-1),(14,-1),(0,19)]:
        # Recess bowl surrounds the narrow combination pin aperture.
        tool=cyl('Recess',7.5,1.4,(x+dx,yy,152.25),axis='Z',verts=32)
        cut(face,tool)
        cut(face,box('Pin_Slot',(10.5,4.2,8),(x+dx,yy,151),bevel=.7))
        cut(face,box('Pin_Slot',(4.2,10.5,8),(x+dx,yy-1,151),bevel=.65))
        if yy==-1:
            cut(face,cyl('Round_Pin',2.5,8,(x+dx+(-2 if dx<0 else 2),yy+1,151),verts=20))
    # Molded underside catches and alignment posts remain part of the faceplate object.
    catches=[]
    for xx in [-30.5,30.5]:
        for yy in [-22,22]:
            catches.append(box('Faceplate_Clip',(1.5,5,9),(x+xx,yy,145),black,group,bevel=.2))
            catches.append(box('Clip_Hook',(2,5,2),(x+math.copysign(29.75,xx),yy,141),black,group,bevel=.2))
    face=join([face]+catches,pre+'Faceplate'); origin_at(face,(x,0,151)); face['assembled_location_m']=[x*.001,0,.0435]
    logo_o=decal(pre+'PowerConnex_Logo',x,-21,152.53,group)
    decorations=[logo_o]
    for text,dx,yy,size in [('L',-25,2,2.4),('N',25,2,2.4),('13A',-20,27,2),('250V~',20,27,2)]:
        decorations.append(label(pre+'Marking_'+text.replace('~','AC'),text,(x+dx,yy,152.54),size,group))
    bpy.context.view_layer.update()
    for decoration in decorations:
        world=decoration.matrix_world.copy()
        decoration.parent=face
        decoration.matrix_parent_inverse.identity()
        decoration.matrix_basis=face.matrix_world.inverted() @ world
        decoration['interaction_owner']=face.name
        decoration['assembled_location_m']=list(decoration.location)

# Every mesh receives pose metadata, deterministic names, and translation-friendly origins.
for o in product.objects:
    if o.type=='MESH':
        if o.parent.name.startswith('Outlet_') and not o.get('interaction_owner'):
            o.location.x += (int(o.parent.name[-2:])-2.5)*.011
        if o.data.materials:
            for polygon in o.data.polygons: polygon.material_index=0
            while len(o.data.materials)>1: o.data.materials.pop(index=len(o.data.materials)-1)
        o['exploded_location_m']=list(o.location)
        o['assembled_rotation_euler']=list(o.rotation_euler)
        if 'assembled_location_m' not in o: raise RuntimeError('Missing assembled pose: '+o.name)
        a=o['assembled_location_m']; e=o.location
        o['assembled_location_gltf_m']=[a[0],a[2],-a[1]]
        o['exploded_location_gltf_m']=[e[0],e[2],-e[1]]
        o.data.name=o.name+'_Mesh'

# Share identical repeated geometry without joining separately selectable components.
import hashlib
mesh_cache={}
for o in product.objects:
    if o.type!='MESH': continue
    me=o.data
    signature=(tuple(tuple(round(c,7) for c in v.co) for v in me.vertices),
        tuple(tuple(p.vertices) for p in me.polygons),tuple(m.name for m in me.materials),
        tuple(tuple(round(c,6) for c in uv.uv) for uv in me.uv_layers.active.data) if me.uv_layers.active else ())
    key=hashlib.sha256(repr(signature).encode()).hexdigest()
    if key in mesh_cache: o.data=mesh_cache[key]
    else: mesh_cache[key]=me

# Reference images are packed but hidden from exported/runtime content.
for i in range(1,4):
    image=bpy.data.images.load(os.path.join(ROOT,'Description-%d.jpg'%i),check_existing=True); image.pack()
    o=bpy.data.objects.new('Reference_Description_%d'%i,None); refs.objects.link(o); o.empty_display_type='IMAGE'; o.data=image
    o.empty_display_size=.35; o.location=(0,.35+i*.02,.15)

floor_mat=material('Studio_Warm_White',(.68,.66,.62),0,.77)
floor=box('Studio_Ground',(2000,2000,2),(0,0,-2),floor_mat,parent=None,bevel=0)
move_coll(floor,studio)
world=bpy.data.worlds.new('Studio_World'); scene.world=world; world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs['Color'].default_value=(.7,.73,.78,1); bg.inputs['Strength'].default_value=.45
def aim(o,point): o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
for name,pos,power,size in [('Key',(-.25,-.3,.55),3.5,.4),('Fill',(.3,-.1,.35),2,.3),('Rim',(0,.3,.5),4,.3)]:
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size
    o=bpy.data.objects.new(name,data); studio.objects.link(o); o.location=pos; aim(o,(0,0,.065))
cameras=[]
for name,pos in [('Camera_Reference_3',(-.47,-.68,.34)),('Camera_Reference_2',(0,-.64,.60)),('Camera_Reference_1',(.46,-.60,.55))]:
    data=bpy.data.cameras.new(name); data.type='ORTHO'; data.ortho_scale=.56; data.lens=55; data.clip_start=.001; data.clip_end=100
    o=bpy.data.objects.new(name,data); studio.objects.link(o); o.location=pos; aim(o,(0,0,.075)); cameras.append(o)
scene.camera=cameras[0]
scene.render.engine='CYCLES'; scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1400; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
scene.cursor.location=(0,0,0)
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True); bpy.context.view_layer.objects.active=root
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.clip_start=.001
            area.spaces.active.region_3d.view_distance=.65
            area.spaces.active.region_3d.view_location=(0,0,.075)
            area.spaces.active.region_3d.view_rotation=cameras[0].rotation_euler.to_quaternion()
            area.spaces.active.shading.type='MATERIAL'

# Reproducible inventory, native file, and uncompressed broadly compatible GLB.
inventory=[]
deps=bpy.context.evaluated_depsgraph_get(); triangles=0
for o in product.objects:
    if o.type=='MESH':
        ev=o.evaluated_get(deps); me=ev.to_mesh(); me.calc_loop_triangles(); n=len(me.loop_triangles); triangles+=n; ev.to_mesh_clear()
        inventory.append(dict(name=o.name,parent=o.parent.name,interaction_owner=o.get('interaction_owner'),triangles=n,assembled_location_m=list(o['assembled_location_m']),exploded_location_m=list(o.location),assembled_location_gltf_m=list(o['assembled_location_gltf_m']),exploded_location_gltf_m=list(o['exploded_location_gltf_m'])))
assert triangles<100000, triangles
with open(os.path.join(OUT,'parts_inventory.json'),'w') as f: json.dump(dict(assembly_version=2,units='meters',mesh_count=len(inventory),interactive_part_count=sum(not p['interaction_owner'] for p in inventory),triangles=triangles,parts=inventory),f,indent=2)
for o in product.objects: o.select_set(True)
floor.select_set(False)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'powerconnex_exploded.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
bpy.ops.object.select_all(action='DESELECT'); root.select_set(True)
scene.camera=cameras[0]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'powerconnex_exploded.blend'))
import shutil
web_assets=os.path.join(ROOT,'web','public','assets')
os.makedirs(web_assets,exist_ok=True)
for asset in ['powerconnex_exploded.glb','parts_inventory.json']:
    shutil.copy2(os.path.join(OUT,asset),os.path.join(web_assets,asset))
def render_single_preview(pose, view):
    mapping={'iso':'Camera_Reference_3','front':'Camera_Reference_2','top':'Camera_Reference_1'}
    camera=bpy.data.objects[mapping[view]]
    previous_camera=scene.camera; previous_path=scene.render.filepath
    previous_matrix=camera.matrix_world.copy(); previous_scale=camera.data.ortho_scale
    previous_samples=scene.cycles.samples
    meshes=[o for o in product.objects if o.type=='MESH']
    positions={o.name:o.location.copy() for o in meshes}
    try:
        for o in meshes: o.location=o['assembled_location_m' if pose=='assembled' else 'exploded_location_m']
        scene.camera=camera; scene.cycles.samples=32
        if pose=='assembled':
            camera.location={'iso':(-.44,-.58,.45),'front':(0,-.65,.025),'top':(0,0,.65)}[view]
            aim(camera,(0,0,.025)); camera.data.ortho_scale=.46
            filename='preview_assembled_'+view+'.png'
        else:
            filename='preview_reference_'+{'iso':'3','front':'2','top':'1'}[view]+'.png'
        scene.render.filepath=os.path.join(OUT,filename)
        bpy.ops.render.render(write_still=True)
        if pose=='exploded' and view=='iso':
            import shutil
            shutil.copy2(scene.render.filepath,os.path.join(ROOT,'web','public','assets','model-preview.png'))
    finally:
        for o in meshes: o.location=positions[o.name]
        camera.matrix_world=previous_matrix; camera.data.ortho_scale=previous_scale
        scene.camera=previous_camera; scene.render.filepath=previous_path; scene.cycles.samples=previous_samples

if globals().get('RENDER_PREVIEWS', True):
    for pose in ['exploded','assembled']:
        for view in ['iso','front','top']: render_single_preview(pose,view)
scene.camera=cameras[0]
print('BUILD_COMPLETE',len(inventory),'mesh objects;',triangles,'triangles')
