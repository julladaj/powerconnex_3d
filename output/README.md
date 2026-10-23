# Power Connex — reference reconstruction

โมเดลรางไฟ 4 เต้ารับ สร้างจาก Description-1.jpg ถึง Description-3.jpg โดยใช้รูปที่ 3 เป็นหลักในการจัด exploded view

## ไฟล์

- `powerconnex_exploded.blend`: โมเดลแก้ไขได้ แยกชิ้นส่วน พร้อมวัสดุ รูปอ้างอิงที่ pack ไว้ และกล้องตรวจสอบ 3 มุม
- `powerconnex_exploded.glb`: โมเดลสำหรับเว็บ มีชื่อ hierarchy วัสดุ และโลโก้ฝังในไฟล์ ไม่รวมฉากสตูดิโอ
- `preview_reference_1.png` ถึง `preview_reference_3.png`: ภาพของโมเดลเดียวกันจากสามมุมใกล้เคียงภาพอ้างอิง ไม่ใช่การสร้างโมเดลสามตัว
- `parts_inventory.json`: รายชื่อชิ้นส่วน จำนวน triangles และตำแหน่งประกอบ/แยกชิ้น
- `validation_report.json`: ผลตรวจโครงสร้างไฟล์และนำ GLB กลับเข้า Blender

## ชิ้นส่วนและสเกล

เลือกชิ้นส่วนภายใต้ `PRODUCT > PowerConnex_PowerStrip` โดยชุดเต้ารับใช้ชื่อ `Outlet_01` ถึง `Outlet_04` ไล่ตามแกน X ติดลบไปบวก มี 77 mesh objects และ 57 ชิ้นที่เลือกจัดการได้บนเว็บ โลโก้และตัวอักษร 20 ชิ้นเป็นลูกของฝา ย้ายแยกไม่ได้ ชิ้นส่วนซ้ำบางชิ้นใช้ mesh data และวัสดุร่วมกันเพื่อลดขนาดไฟล์ หากจะแก้รูปทรงชิ้นเดียว ให้ใช้ Make Single User ก่อน

ใช้เมตรเป็นหน่วยข้อมูล ความยาวตัวรางประมาณ 0.300 เมตร กว้าง 0.065 เมตร สูง 0.042 เมตร ไม่รวมเต้ารับและขายึด ไม่มีขนาดจริงในภาพ ดังนั้นขนาดทั้งหมดเป็นค่าประมาณ สามารถปรับสเกลทั้งโมเดลผ่าน root ได้

ชื่อเช่น `Molded_Outlet_Body`, `Safety_Shutter`, `Industrial_Spring`, `Copper_Coated_Nickel_Contact`, `Solid_Copper_Bar`, `PVC_Insulation_Liner`, `End_Plate` และ `Mounting_Bracket` อ้างอิงคำบรรยายและลักษณะของชิ้นส่วนในภาพ

## เปลี่ยนระหว่างประกอบและแยกชิ้น

ค่าเริ่มต้นคือ exploded view ไม่มี animation โลโก้และตัวอักษรใช้ local pose คงที่ตาม parent ฝา ชิ้นส่วนอื่นแต่ละชิ้นมี custom properties เก็บตำแหน่งทั้งสองสถานะ ใน Blender ใช้ Python Console:

```python
for o in bpy.data.collections['PRODUCT'].objects:
    if o.type == 'MESH':
        o.location = o['assembled_location_m']
```

เปลี่ยนกลับเป็น `o['exploded_location_m']` เพื่อคืน exploded view ทั้งสองค่าเป็น local translation ในหน่วยเมตร parent ของแต่ละชิ้นเริ่มต้นเป็น identity

บนเว็บใช้ `object.userData.assembled_location_gltf_m` และ `object.userData.exploded_location_gltf_m` กับ local position ของ mesh node เมื่อ loader รองรับ glTF extras ค่าเหล่านี้แปลงเป็นแกน glTF Y-up แล้ว อย่าใช้ `_location_m` ของ Blender กับ GLB โดยตรง

## ความเที่ยงตรงและข้อจำกัด

รูเสียบ ร่องล็อก ขายึด สปริง และรายละเอียดที่มีผลต่อ silhouette เป็น geometry จริง โลโก้ใช้ภาพ crop จาก artwork ที่ให้มา ส่วนตัวอักษรบนหน้าเต้ารับเป็น mesh บางเพื่อรักษาความคมชัดในไฟล์ GLB

เป็นการจำลองจากภาพเพื่อแสดงผล ไม่ใช่ CAD สำหรับผลิต รูปทรงหน้าสัมผัส ทางเดินตัวนำสามเส้น ฉนวน และรายละเอียดที่ภาพบังอยู่เป็นการประมาณ ไม่มีการรับรองความแม่นยำทางไฟฟ้า วัสดุเป็นการจำลองลักษณะผิวจากภาพ ไม่ใช่ข้อมูลวัสดุที่วัดจริง

ลดขนาดโดยแชร์วัสดุและ mesh ซ้ำภายใน Blender และใช้ GLB มาตรฐานโดยไม่ต้องติดตั้ง decoder ไม่ได้ใช้ glTF Transform เนื่องจากสภาพแวดล้อมเชื่อมต่อ npm registry ไม่ได้ ไม่ได้ทดสอบใน browser engine จริง แต่ตรวจ GLB ด้วยการนำกลับเข้า Blender

## สร้างใหม่

เปิด Blender Scripting แล้วรัน `build_model.py` จากโฟลเดอร์หลัก สคริปต์จะล้าง scene ปัจจุบัน จึงควรรันในไฟล์ใหม่ ค่าเริ่มต้นสร้างโมเดล ส่งออก และเรนเดอร์ทั้งสามมุม จากนั้นรัน `validate_model.py` ใน scene ที่สร้างเสร็จเพื่อตรวจไฟล์
