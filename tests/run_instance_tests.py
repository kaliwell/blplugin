# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import os
import pathlib
import sys
import tempfile

import bpy


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

addon = importlib.import_module("collection_mask_exporter")
addon.register()
scene = bpy.context.scene
scene.render.resolution_x = 128
scene.render.resolution_y = 64
scene.render.resolution_percentage = 100

camera_data = bpy.data.cameras.new("InstanceCamera")
camera = bpy.data.objects.new("InstanceCamera", camera_data)
scene.collection.objects.link(camera)
camera.location = (0.0, 0.0, 8.0)
scene.camera = camera


def source_cube(name):
    source = bpy.data.collections.new(name + "Source")
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.object
    cube.name = name + "Mesh"
    for owner in list(cube.users_collection):
        owner.objects.unlink(cube)
    source.objects.link(cube)
    return source


def collection_instance(name, source, location=(0.0, 0.0, 0.0)):
    instance = bpy.data.objects.new(name, None)
    instance.instance_type = "COLLECTION"
    instance.instance_collection = source
    instance.location = location
    return instance


left_group = bpy.data.collections.new("CM_InstanceLeft")
right_group = bpy.data.collections.new("CM_InstanceRight")
scene.collection.children.link(left_group)
scene.collection.children.link(right_group)

left_inner = source_cube("LeftDeep")
left_outer = bpy.data.collections.new("LeftOuterSource")
left_nested = collection_instance("LeftNestedInstance", left_inner)
left_outer.objects.link(left_nested)
left_host = collection_instance("LeftHost", left_outer, (-1.5, 0.0, 0.0))
left_group.objects.link(left_host)

right_source = source_cube("Right")
right_host = collection_instance("RightHost", right_source, (1.5, 0.0, 0.0))
right_group.objects.link(right_host)

# Production files commonly keep instance sources linked to the Scene but
# excluded from the active View Layer. Their objects must not disappear from
# the rendered instances when CMask configures ordinary scene objects.
scene.collection.children.link(left_inner)
scene.collection.children.link(left_outer)
scene.collection.children.link(right_source)
from collection_mask_exporter.core.layer_collection import collection_layer_map
source_layers = collection_layer_map(bpy.context.view_layer)
source_layers[left_inner].exclude = True
source_layers[left_outer].exclude = True
source_layers[right_source].exclude = True

settings = scene.cmask_settings
settings.scan_mode = "PREFIX"
assert bpy.ops.cmask.scan() == {"FINISHED"}
assert len(settings.groups) == 2
assert bpy.ops.cmask.validate() == {"FINISHED"}
assert not any(issue.code == "EMPTY" for issue in settings.issues)

output = pathlib.Path(tempfile.mkdtemp(prefix="cmask-instance-test-"))
settings.output_directory = str(output)
settings.output_format = "PNG"
settings.mask_output_mode = "VISIBLE"

from collection_mask_exporter.core.output_manager import color_id_path, mask_path
from collection_mask_exporter.core.render_pipeline import render_color_id, render_mask

id_path = color_id_path(scene, settings)
render_color_id(bpy.context, id_path)
image = bpy.data.images.load(id_path, check_existing=False)
try:
    pixels = list(image.pixels)
    opaque = [tuple(round(pixels[index + channel], 2) for channel in range(3))
              for index in range(0, len(pixels), 4) if pixels[index + 3] > 0.95]
finally:
    bpy.data.images.remove(image)
assert opaque, "Collection Instance 彩色 ID 没有可见像素"
assert len(set(opaque)) >= 2, "两个实例组没有得到独立 Collection 颜色"

for item in settings.groups:
    path = mask_path(scene, settings, item.collection.name)
    render_mask(bpy.context, item, path)
    image = bpy.data.images.load(path, check_existing=False)
    try:
        pixels = list(image.pixels)
        width, height = image.size
        alpha = pixels[3::4]
        left_alpha = sum(alpha[y * width + x]
                         for y in range(height) for x in range(width // 2))
        right_alpha = sum(alpha[y * width + x]
                          for y in range(height) for x in range(width // 2, width))
    finally:
        bpy.data.images.remove(image)
    if item.collection == left_group:
        assert left_alpha > 10.0 and right_alpha < 0.01
    else:
        assert right_alpha > 10.0 and left_alpha < 0.01

right_item = next(item for item in settings.groups
                  if item.collection == right_group)
right_mesh = next(obj for obj in right_source.objects if obj.type == "MESH")
transparent = bpy.data.materials.new("InstanceTransparent")
transparent.diffuse_color = (1.0, 1.0, 1.0, 0.25)
right_mesh.data.materials.append(transparent)
from collection_mask_exporter.core.transparency import object_uses_transparency
assert object_uses_transparency(right_host), "没有识别实例源透明材质"
settings.transparent_material_mode = "EXCLUDE"
excluded_path = str(output / "instance-transparent-excluded.png")
render_mask(bpy.context, right_item, excluded_path)
image = bpy.data.images.load(excluded_path, check_existing=False)
try:
    excluded_alpha = sum(list(image.pixels)[3::4])
finally:
    bpy.data.images.remove(image)
assert excluded_alpha < 0.01, "实例源透明材质没有按策略排除宿主实例"
settings.transparent_material_mode = "INCLUDE"

assert left_host.hide_render is False and right_host.hide_render is False
assert left_nested.hide_render is False
assert os.path.isfile(id_path)
print("CMASK COLLECTION INSTANCE TESTS PASSED")
addon.unregister()
