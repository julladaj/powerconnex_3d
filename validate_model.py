"""Run in the finished Blender scene; verify export and import in an isolated scene."""
import bpy, os, json, math, struct
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(ROOT,'output')
path=os.path.join(OUT,'powerconnex_exploded.glb')
original=bpy.context.scene
source={o.name:o for o in bpy.data.collections['PRODUCT'].objects if o.type=='MESH'}
with open(path,'rb') as f: data=f.read()
magic,version,length=struct.unpack_from('<4sII',data)
assert magic==b'glTF' and version==2 and length==len(data)
n,kind=struct.unpack_from('<I4s',data,12)
doc=json.loads(data[20:20+n])
names={n['name'] for n in doc['nodes'] if 'mesh' in n}
assert names==set(source), (names-set(source),set(source)-names)
assert not any('Studio' in n.get('name','') or 'Camera_' in n.get('name','') for n in doc['nodes'])
assert all('uri' not in image for image in doc.get('images',[]))
assert len(data)<10*1024*1024
tris=0
for mesh in doc['meshes']:
    for p in mesh['primitives']:
        assert p.get('mode',4)==4
        assert 'POSITION' in p['attributes'] and 'NORMAL' in p['attributes']
for node in doc['nodes']:
    if 'mesh' not in node: continue
    assert all(math.isfinite(x) for x in node.get('translation',[0,0,0]))
    assert 'assembled_location_gltf_m' in node['extras']
    for p in doc['meshes'][node['mesh']]['primitives']:
        tris+=doc['accessors'][p['indices']]['count']//3
assert tris<100000

temp=bpy.data.scenes.new('GLB_ROUNDTRIP_VALIDATION')
bpy.context.window.scene=temp
try:
    bpy.ops.import_scene.gltf(filepath=path)
    imported=[o for o in temp.objects if o.type=='MESH']
    assert len(imported)==len(source),(len(imported),len(source))
    for o in imported:
        name=o.name.rsplit('.',1)[0] if o.name.rsplit('.',1)[-1].isdigit() else o.name
        assert name in source,name
        # Blender importer restores original Z-up coordinates.
        expected=source[name]
        assert (o.matrix_world.translation-expected.matrix_world.translation).length<1e-6,name
        for a,b in zip(sorted(o.dimensions),sorted(expected.dimensions)):
            assert abs(a-b)<2e-6,(name,list(o.dimensions),list(expected.dimensions))
        assert len(o.data.materials)>0,name
        assert o.get('interaction_owner')==expected.get('interaction_owner'),name
        assert list(o['assembled_location_gltf_m'])==list(expected['assembled_location_gltf_m']),name
finally:
    bpy.context.window.scene=original
    for o in list(temp.objects): bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.scenes.remove(temp)

import ast
from mathutils import Vector
tree=ast.parse(open(os.path.join(ROOT,'build_model.py')).read())
origin_function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='origin_at')
namespace={'Vector':Vector}
exec(compile(ast.Module(body=[origin_function],type_ignores=[]),'origin_regression','exec'),namespace)
# Shared data and multiple selected objects reproduce both original failure modes.
mesh=bpy.data.meshes.new('Origin_Regression_Data')
mesh.from_pydata([(0,0,0),(.01,0,0),(0,.01,0)],[],[(0,1,2)])
target=bpy.data.objects.new('Origin_Regression_Target',mesh)
bystander=bpy.data.objects.new('Origin_Regression_Bystander',mesh)
original.collection.objects.link(target); original.collection.objects.link(bystander)
bpy.ops.object.select_all(action='DESELECT')
target.select_set(True); bystander.select_set(True)
target.location=(.1,.2,.3); bystander.location=(-.1,0,0)
bpy.context.view_layer.update()
before=[target.matrix_world @ v.co for v in target.data.vertices]
other_before=[bystander.matrix_world @ v.co for v in bystander.data.vertices]
namespace['origin_at'](target,(120,230,340))
bpy.context.view_layer.update()
assert all((a-target.matrix_world @ v.co).length<1e-7 for a,v in zip(before,target.data.vertices))
assert all((a-bystander.matrix_world @ v.co).length<1e-7 for a,v in zip(other_before,bystander.data.vertices))
assert (target.location-Vector((.12,.23,.34))).length<1e-7
bpy.data.objects.remove(target,do_unlink=True); bpy.data.objects.remove(bystander,do_unlink=True)
report=dict(status='PASS',assembly_version=2,mesh_objects=len(source),interactive_parts=sum(not o.get('interaction_owner') for o in source.values()),triangles=tris,glb_bytes=len(data),materials=len(doc['materials']),unique_exported_meshes=len(doc['meshes']),embedded_images=len(doc.get('images',[])),checks=['GLB container and scene structure','All individually named mesh nodes retained','No studio cameras, lights or ground exported','All textures embedded','Pose metadata and attachment ownership retained','Triangle and size budgets','GLB reimport: mesh count, dimensions, world positions, materials','Origin rebasing preserves target geometry and selected bystander with shared mesh data'])
with open(os.path.join(OUT,'validation_report.json'),'w') as f: json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
