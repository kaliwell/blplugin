# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import pathlib
import sys
import tempfile

import bmesh
import bpy
from mathutils import Matrix, Vector


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

addon = importlib.import_module("collection_mask_exporter")
addon.register()
scene = bpy.context.scene
scene.render.resolution_x = 128
scene.render.resolution_y = 64
scene.render.resolution_percentage = 100

camera_data = bpy.data.cameras.new("DynamicCamera")
camera = bpy.data.objects.new("DynamicCamera", camera_data)
scene.collection.objects.link(camera)
camera.location = (0.0, -12.0, 0.0)
camera.rotation_euler = (Vector((0.0, 0.0, 0.0)) - camera.location).to_track_quat(
    "-Z", "Y"
).to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 6.0
scene.camera = camera

host_group = bpy.data.collections.new("CM_DynamicHost")
left_group = bpy.data.collections.new("CM_DynamicLeft")
right_group = bpy.data.collections.new("CM_DynamicRight")
scene.collection.children.link(host_group)
scene.collection.children.link(left_group)
scene.collection.children.link(right_group)

mesh = bpy.data.meshes.new("DynamicHostMesh")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0, matrix=Matrix.Translation((-1.5, 0.0, 0.0)))
bmesh.ops.create_cube(bm, size=2.0, matrix=Matrix.Translation((1.5, 0.0, 0.0)))
bm.to_mesh(mesh)
bm.free()
attribute = mesh.attributes.new("cmask_id", "INT", "FACE")
for polygon in mesh.polygons:
    attribute.data[polygon.index].value = 1 if polygon.center.x < 0.0 else 2

host = bpy.data.objects.new("DynamicHost", mesh)
host_group.objects.link(host)
tree = bpy.data.node_groups.new("DynamicPassThrough", "GeometryNodeTree")
tree.interface.new_socket(
    name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
)
tree.interface.new_socket(
    name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
)
group_input = tree.nodes.new("NodeGroupInput")
group_output = tree.nodes.new("NodeGroupOutput")
tree.links.new(group_input.outputs["Geometry"], group_output.inputs["Geometry"])
modifier = host.modifiers.new("Dynamic Geometry Nodes", "NODES")
modifier.node_group = tree

settings = scene.cmask_settings
settings.scan_mode = "PREFIX"
settings.output_directory = tempfile.mkdtemp(prefix="cmask-dynamic-test-")
settings.dynamic_geometry_enabled = True
settings.dynamic_attribute_name = "cmask_id"
settings.output_format = "PNG"
settings.mask_output_mode = "VISIBLE"
assert bpy.ops.cmask.scan() == {"FINISHED"}
for item in settings.groups:
    if item.collection == host_group:
        item.role = "IGNORE"
    elif item.collection == left_group:
        item.dynamic_id = 1
        item.color = (1.0, 0.05, 0.05, 1.0)
    elif item.collection == right_group:
        item.dynamic_id = 2
        item.color = (0.05, 0.2, 1.0, 1.0)

from collection_mask_exporter.core.output_manager import color_id_path, mask_path
from collection_mask_exporter.core.render_pipeline import render_color_id, render_mask
from collection_mask_exporter.core.conflict_checker import validate_groups

left_item = next(item for item in settings.groups if item.collection == left_group)
right_item = next(item for item in settings.groups if item.collection == right_group)
right_item.dynamic_id = 1
issues, _resolution = validate_groups(settings)
assert any(issue.code == "DYNAMIC_GN_DUPLICATE_ID" for issue in issues)
right_item.dynamic_id = 2

settings.dynamic_attribute_name = "missing_cmask_id"
try:
    render_color_id(bpy.context, color_id_path(scene, settings))
except RuntimeError as exc:
    assert "missing_cmask_id" in str(exc)
else:
    raise AssertionError("missing dynamic attribute did not block export")
assert not any(item.name.startswith("__CMASK_DYNAMIC") for item in bpy.data.objects)
settings.dynamic_attribute_name = "cmask_id"

id_path = color_id_path(scene, settings)
render_color_id(bpy.context, id_path)
image = bpy.data.images.load(id_path, check_existing=False)
try:
    pixels = list(image.pixels)
    opaque = [tuple(round(pixels[index + channel], 2) for channel in range(3))
              for index in range(0, len(pixels), 4) if pixels[index + 3] > 0.95]
finally:
    bpy.data.images.remove(image)
assert len(set(opaque)) >= 2, "dynamic color ID did not preserve two cmask_id groups"

for item in settings.groups:
    if item.role != "MASK":
        continue
    path = mask_path(scene, settings, item.collection.name)
    render_mask(bpy.context, item, path)
    image = bpy.data.images.load(path, check_existing=False)
    try:
        pixels = list(image.pixels)
        width, height = image.size
        alpha = pixels[3::4]
        left = sum(alpha[y * width + x]
                   for y in range(height) for x in range(width // 2))
        right = sum(alpha[y * width + x]
                    for y in range(height) for x in range(width // 2, width))
    finally:
        bpy.data.images.remove(image)
    if item.dynamic_id == 1:
        assert left > 10.0 and right < 0.01, (left, right)
    else:
        assert right > 10.0 and left < 0.01, (left, right)

assert not any(item.name.startswith("__CMASK_DYNAMIC") for item in bpy.data.objects)
assert not any(item.name.startswith("__CMASK_DYNAMIC") for item in bpy.data.collections)
assert not any(item.name.startswith("__CMASK_DYNAMIC") for item in bpy.data.meshes)
print("CMASK DYNAMIC GEOMETRY TESTS PASSED")
addon.unregister()
