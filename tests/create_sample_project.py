# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import pathlib
import sys

import bpy
from mathutils import Vector


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

bpy.ops.wm.read_factory_settings(use_empty=True)
addon = importlib.import_module("collection_mask_exporter")
addon.register()
scene = bpy.context.scene
scene.name = "CMask Demo"
if hasattr(bpy.context.preferences.filepaths, "save_version"):
    bpy.context.preferences.filepaths.save_version = 0
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100


def collection(name):
    result = bpy.data.collections.new(name)
    scene.collection.children.link(result)
    return result


def move_to(obj, target):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)


def material(name, color):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    return result


def cube(name, target, location, scale, color, bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to(obj, target)
    obj.data.materials.append(material(name + " Material", color))
    modifier = obj.modifiers.new("Soft Edges", "BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    return obj


body = collection("CM_Body")
detail = collection("CM_Detail")
occluder = collection("CM_Occluder")
holdout = collection("CM_Holdout")

cube("Body", body, (-1.2, 0.0, 0.0), (1.25, 0.8, 1.25), (0.12, 0.32, 0.8))
cube("Detail", detail, (1.2, 0.0, 0.0), (1.0, 0.65, 0.9), (0.9, 0.25, 0.08))
cube("Foreground Occluder", occluder, (0.0, -1.0, -0.45),
     (0.35, 0.25, 1.4), (0.08, 0.08, 0.08), bevel=0.05)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24,
                                     location=(0.0, -0.35, 0.55), radius=0.42)
cutout = bpy.context.object
cutout.name = "Holdout Cutout"
move_to(cutout, holdout)
cutout.data.materials.append(material("Holdout Preview", (0.6, 0.1, 0.7)))

camera_data = bpy.data.cameras.new("CMask Demo Camera")
camera = bpy.data.objects.new("CMask Demo Camera", camera_data)
scene.collection.objects.link(camera)
camera.location = (0.0, -12.0, 4.2)
direction = Vector((0.0, 0.0, 0.15)) - camera.location
camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 6.5
scene.camera = camera

settings = scene.cmask_settings
settings.scan_mode = "PREFIX"
settings.collection_prefix = "CM_"
settings.include_children = True
settings.output_directory = "//CMask_Demo_Output/"
settings.filename_template = "{blend}_{collection}_{mode}"
settings.output_format = "PNG"
settings.color_depth = "16"
settings.mask_output_mode = "VISIBLE"
settings.alpha_mode = "STRAIGHT"
settings.mask_use_group_name = True
settings.mask_use_group_color = True
settings.write_report = True
settings.photoshop_create_channels = True
assert bpy.ops.cmask.scan() == {"FINISHED"}

roles = {
    "CM_Body": ("MASK", (0.95, 0.08, 0.08, 1.0)),
    "CM_Detail": ("MASK", (0.08, 0.95, 0.12, 1.0)),
    "CM_Occluder": ("OCCLUDER", (0.08, 0.18, 0.95, 1.0)),
    "CM_Holdout": ("HOLDOUT", (0.95, 0.75, 0.08, 1.0)),
}
for item in settings.groups:
    item.role, item.color = roles[item.collection.name]

settings.preset_name = "演示交付"
assert bpy.ops.cmask.save_preset() == {"FINISHED"}
assert bpy.ops.cmask.validate() == {"FINISHED"}
assert not any(issue.level == "ERROR" for issue in settings.issues)

scene["cmask_demo_readme"] = (
    "打开 3D Viewport > N 面板 > Collection Mask，检查场景后执行全部导出。"
)
output = ROOT / "examples" / "CMask_Demo.blend"
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
print("CMASK SAMPLE CREATED", output)
