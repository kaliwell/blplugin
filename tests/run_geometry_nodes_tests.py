# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import json
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

camera_data = bpy.data.cameras.new("GeometryNodesCamera")
camera = bpy.data.objects.new("GeometryNodesCamera", camera_data)
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
    return source, cube


def geometry_host(name, source, location):
    mesh = bpy.data.meshes.new(name + "Mesh")
    host = bpy.data.objects.new(name, mesh)
    host.location = location
    tree = bpy.data.node_groups.new(name + "Nodes", "GeometryNodeTree")
    tree.interface.new_socket(
        name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    output = tree.nodes.new("NodeGroupOutput")
    info = tree.nodes.new("GeometryNodeCollectionInfo")
    info.inputs["Collection"].default_value = source
    realize = tree.nodes.new("GeometryNodeRealizeInstances")
    tree.links.new(info.outputs["Instances"], realize.inputs["Geometry"])
    tree.links.new(realize.outputs["Geometry"], output.inputs["Geometry"])
    modifier = host.modifiers.new("CMask Geometry Nodes", "NODES")
    modifier.node_group = tree
    return host


left_group = bpy.data.collections.new("CM_GeometryLeft")
right_group = bpy.data.collections.new("CM_GeometryRight")
scene.collection.children.link(left_group)
scene.collection.children.link(right_group)
left_source, left_mesh = source_cube("GeometryLeft")
right_source, right_mesh = source_cube("GeometryRight")
left_host = geometry_host("GeometryLeftHost", left_source, (-1.5, 0.0, 0.0))
right_host = geometry_host("GeometryRightHost", right_source, (1.5, 0.0, 0.0))
left_group.objects.link(left_host)
right_group.objects.link(right_host)

# Keep source Collections scene-linked but hidden as original occurrences.
scene.collection.children.link(left_source)
scene.collection.children.link(right_source)
from collection_mask_exporter.core.layer_collection import collection_layer_map
source_layers = collection_layer_map(bpy.context.view_layer)
source_layers[left_source].exclude = True
source_layers[right_source].exclude = True

settings = scene.cmask_settings
settings.scan_mode = "PREFIX"
assert bpy.ops.cmask.scan() == {"FINISHED"}
assert len(settings.groups) == 2
assert bpy.ops.cmask.validate() == {"FINISHED"}
assert not settings.issues[:]

from collection_mask_exporter.core.group_resolver import resolve_groups
resolution = resolve_groups(settings.groups, settings.include_children)
assert left_mesh in resolution.geometry_node_sources[left_host]
assert right_mesh in resolution.geometry_node_sources[right_host]

output = pathlib.Path(tempfile.mkdtemp(prefix="cmask-geometry-nodes-test-"))
settings.output_directory = str(output)
settings.output_format = "PNG"
settings.mask_output_mode = "VISIBLE"

from collection_mask_exporter.core.output_manager import color_id_path, mask_path
from collection_mask_exporter.core.render_pipeline import render_color_id, render_mask

original = {
    obj: (tuple(obj.color), bool(obj.hide_render), bool(obj.is_holdout))
    for obj in (left_host, right_host, left_mesh, right_mesh)
}
id_path = color_id_path(scene, settings)
render_color_id(bpy.context, id_path)
image = bpy.data.images.load(id_path, check_existing=False)
try:
    pixels = list(image.pixels)
    opaque = [tuple(round(pixels[index + channel], 2) for channel in range(3))
              for index in range(0, len(pixels), 4) if pixels[index + 3] > 0.95]
finally:
    bpy.data.images.remove(image)
assert opaque, "Geometry Nodes Collection Info 没有可见像素"
assert len(set(opaque)) >= 2, "两个 Geometry Nodes 宿主没有独立 Collection 颜色"

from collection_mask_exporter.core.report_manager import write_export_report
report_path = write_export_report(
    scene, settings, "geometry_nodes_test", [id_path], 0.0
)
with open(report_path, "r", encoding="utf-8") as handle:
    report = json.load(handle)
assert sorted(item["host"] for item in report["geometry_nodes"]) == [
    "GeometryLeftHost", "GeometryRightHost",
]
assert all(item["resolved_sources"] for item in report["geometry_nodes"])

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

transparent = bpy.data.materials.new("GeometryNodesTransparent")
transparent.diffuse_color = (1.0, 1.0, 1.0, 0.25)
right_mesh.data.materials.append(transparent)
from collection_mask_exporter.core.transparency import object_uses_transparency
assert object_uses_transparency(right_host)
settings.transparent_material_mode = "EXCLUDE"
right_item = next(item for item in settings.groups
                  if item.collection == right_group)
excluded_path = str(output / "geometry-nodes-transparent-excluded.png")
render_mask(bpy.context, right_item, excluded_path)
image = bpy.data.images.load(excluded_path, check_existing=False)
try:
    assert sum(list(image.pixels)[3::4]) < 0.01
finally:
    bpy.data.images.remove(image)

for obj, state in original.items():
    assert tuple(obj.color) == state[0]
    assert bool(obj.hide_render) == state[1]
    assert bool(obj.is_holdout) == state[2]

print("CMASK GEOMETRY NODES TESTS PASSED")
addon.unregister()
