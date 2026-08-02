# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import pathlib
import sys
import tempfile

import bpy
from mathutils import Vector


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

addon = importlib.import_module("collection_mask_exporter")
addon.register()
scene = bpy.context.scene
scene.render.resolution_x = 128
scene.render.resolution_y = 64
scene.render.resolution_percentage = 100

camera_data = bpy.data.cameras.new("SplitCamera")
camera = bpy.data.objects.new("SplitCamera", camera_data)
scene.collection.objects.link(camera)
camera.location = (0.0, -12.0, 0.0)
camera.rotation_euler = (Vector((0.0, 0.0, 0.0)) - camera.location).to_track_quat(
    "-Z", "Y"
).to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 6.0
scene.camera = camera

source_root = bpy.data.collections.new("GeometrySplitSource")
left_group = bpy.data.collections.new("CM_SplitLeft")
right_group = bpy.data.collections.new("CM_SplitRight")
host_group = bpy.data.collections.new("CM_SplitHost")
source_root.children.link(left_group)
source_root.children.link(right_group)
scene.collection.children.link(source_root)
scene.collection.children.link(host_group)


def cube(name, target, location):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)
    return obj


left = cube("SplitLeftMesh", left_group, (-1.5, 0.0, 0.0))
right = cube("SplitRightMesh", right_group, (1.5, 0.0, 0.0))
host_mesh = bpy.data.meshes.new("SplitHostMesh")
host = bpy.data.objects.new("SplitHost", host_mesh)
host_group.objects.link(host)
tree = bpy.data.node_groups.new("SplitHostNodes", "GeometryNodeTree")
tree.interface.new_socket(
    name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
)
output_node = tree.nodes.new("NodeGroupOutput")
info = tree.nodes.new("GeometryNodeCollectionInfo")
info.inputs["Collection"].default_value = source_root
realize = tree.nodes.new("GeometryNodeRealizeInstances")
tree.links.new(info.outputs["Instances"], realize.inputs["Geometry"])
tree.links.new(realize.outputs["Geometry"], output_node.inputs["Geometry"])
modifier = host.modifiers.new("CMask Split Geometry Nodes", "NODES")
modifier.node_group = tree

from collection_mask_exporter.core.layer_collection import collection_layer_map
collection_layer_map(bpy.context.view_layer)[source_root].exclude = True

settings = scene.cmask_settings
settings.scan_mode = "PREFIX"
settings.mask_output_mode = "VISIBLE"
settings.output_format = "PNG"
assert bpy.ops.cmask.scan() == {"FINISHED"}
assert len(settings.groups) == 3
assert bpy.ops.cmask.configure_geometry_nodes_split() == {"FINISHED"}
assert settings.geometry_nodes_split_sources
assert next(item for item in settings.groups
            if item.collection == host_group).role == "IGNORE"
assert bpy.ops.cmask.validate() == {"FINISHED"}
assert not any(issue.code == "GEOMETRY_NODES_SOURCE_GROUP"
               for issue in settings.issues)

from collection_mask_exporter.core.group_resolver import resolve_groups
resolution = resolve_groups(settings.groups, True)
assert resolution.geometry_node_sources[host] >= {left, right}
original_states = {
    obj: (tuple(obj.color), bool(obj.hide_render), bool(obj.is_holdout))
    for obj in (host, left, right)
}

output = pathlib.Path(tempfile.mkdtemp(prefix="cmask-geometry-split-test-"))
settings.output_directory = str(output)
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
assert len(set(opaque)) >= 2, "拆分彩色 ID 没有得到两个源组颜色"

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
        left_alpha = sum(alpha[y * width + x]
                         for y in range(height) for x in range(width // 2))
        right_alpha = sum(alpha[y * width + x]
                          for y in range(height) for x in range(width // 2, width))
    finally:
        bpy.data.images.remove(image)
    if item.collection == left_group:
        assert left_alpha > 10.0 and right_alpha < 0.01, (left_alpha, right_alpha)
    else:
        assert right_alpha > 10.0 and left_alpha < 0.01, (left_alpha, right_alpha)

settings.write_report = False
assert bpy.ops.cmask.export_multilayer_exr() == {"FINISHED"}
assert pathlib.Path(settings.last_outputs[0].path).is_file()
assert bpy.ops.cmask.export_cryptomatte() == {"FINISHED"}
assert pathlib.Path(settings.last_outputs[0].path).is_file()

for obj, state in original_states.items():
    assert tuple(obj.color) == state[0]
    assert bool(obj.hide_render) == state[1]
    assert bool(obj.is_holdout) == state[2]

print("CMASK GEOMETRY NODES SPLIT TESTS PASSED")
addon.unregister()
