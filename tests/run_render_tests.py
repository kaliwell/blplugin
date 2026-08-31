# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import json
import os
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


def link_only(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def create_scene():
    scene = bpy.context.scene
    scene.render.resolution_x = 96
    scene.render.resolution_y = 96
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.render.film_transparent = False

    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, 0.0, 7.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    camera.rotation_euler.rotate_axis("X", 0.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    # Cameras look down local -Z; this placement points directly at the origin.
    scene.camera = camera

    front_collection = bpy.data.collections.new("CM_Front")
    back_collection = bpy.data.collections.new("CM_Back")
    scene.collection.children.link(front_collection)
    scene.collection.children.link(back_collection)

    bpy.ops.mesh.primitive_cube_add(location=(-0.35, 0.0, 1.0), scale=(0.8, 0.8, 0.8))
    front = bpy.context.object
    front.name = "Front"
    link_only(front, front_collection)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12,
                                        location=(0.35, 0.0, 0.0), scale=(1.0, 1.0, 1.0))
    back = bpy.context.object
    back.name = "Back"
    link_only(back, back_collection)

    settings = scene.cmask_settings
    assert settings.mask_edge_protection is False
    settings.scan_mode = "PREFIX"
    bpy.ops.cmask.scan()
    return scene, settings, front, back


def alpha_range(path):
    image = bpy.data.images.load(path, check_existing=False)
    try:
        pixels = list(image.pixels)
        alpha = pixels[3::4]
        return min(alpha), max(alpha), sum(alpha)
    finally:
        bpy.data.images.remove(image)


def opaque_color_spread(path):
    image = bpy.data.images.load(path, check_existing=False)
    try:
        pixels = list(image.pixels)
        colors = [tuple(pixels[index:index + 3])
                  for index in range(0, len(pixels), 4)
                  if pixels[index + 3] > 0.9]
        return (max(color[0] for color in colors) - min(color[0] for color in colors),
                max(color[1] for color in colors) - min(color[1] for color in colors),
                max(color[2] for color in colors) - min(color[2] for color in colors))
    finally:
        bpy.data.images.remove(image)


def closest_opaque_rgb(path, expected):
    image = bpy.data.images.load(path, check_existing=False)
    try:
        pixels = list(image.pixels)
        colors = [tuple(pixels[index:index + 3])
                  for index in range(0, len(pixels), 4)
                  if pixels[index + 3] > 0.99]
        assert colors, "Expected opaque pixels"
        return min(colors, key=lambda color: sum(
            abs(color[channel] - expected[channel]) for channel in range(3)
        ))
    finally:
        bpy.data.images.remove(image)


def fractional_rgba(path):
    image = bpy.data.images.load(path, check_existing=False)
    try:
        if hasattr(image, "alpha_mode"):
            image.alpha_mode = "CHANNEL_PACKED"
        pixels = list(image.pixels)
        candidates = [tuple(pixels[index:index + 4])
                      for index in range(0, len(pixels), 4)
                      if 0.1 < pixels[index + 3] < 0.9]
        assert candidates, "Expected anti-aliased edge pixels"
        return min(candidates, key=lambda rgba: abs(rgba[3] - 0.5))
    finally:
        bpy.data.images.remove(image)


scene, settings, front, back = create_scene()
original_material = bpy.data.materials.new("OriginalMaterial")
front.data.materials.append(original_material)
back.data.materials.append(original_material)
user_named_material = bpy.data.materials.new("__CMASK_MATERIAL_ID")
from collection_mask_exporter.core.material_override import ensure_material_node_tree
original_tree = ensure_material_node_tree(original_material)
original_tree.nodes.clear()
original_output = original_tree.nodes.new("ShaderNodeOutputMaterial")
original_emission = original_tree.nodes.new("ShaderNodeEmission")
original_emission.inputs["Color"].default_value = (0.12, 0.48, 0.86, 1.0)
original_tree.links.new(
    original_emission.outputs["Emission"], original_output.inputs["Surface"]
)
ensure_material_node_tree(user_named_material)
user_named_material.node_tree.nodes[0].name = "UserSentinel"
user_named_layer = scene.view_layers.new("__CMASK_VIEW_LAYER")
user_named_layer["sentinel"] = "keep"
scene.render.use_compositing = True
scene.render.use_sequencer = True
front.color = (0.17, 0.23, 0.31, 1.0)
back.hide_render = False
front.is_holdout = False
original = (scene.render.engine, scene.render.image_settings.file_format,
            scene.render.film_transparent, tuple(front.color), back.hide_render,
            front.is_holdout, scene.render.use_compositing,
            scene.render.use_sequencer, tuple(front.data.materials),
            tuple(back.data.materials))

output = pathlib.Path(tempfile.mkdtemp(prefix="cmask-render-test-"))
settings.output_directory = str(output)

from collection_mask_exporter.core.output_manager import (
    color_id_path, cryptomatte_path, cutout_path, mask_path, multilayer_path,
)
from collection_mask_exporter.core.layer_collection import collection_layer_map
from collection_mask_exporter.core.render_pipeline import (
    TEMP_VIEW_LAYER, _create_view_layer, _remove_view_layer,
    render_color_id, render_cutout, render_mask,
)
from collection_mask_exporter.core.compositor import get_compositor_tree
from collection_mask_exporter.core.state_manager import (
    capture_scene_state, restore_scene_state,
)

# A user resource with the old fixed name must survive untouched, and the
# temporary layer must inherit active-layer collection exclusions.
source_layer = bpy.context.window.view_layer
source_map = collection_layer_map(source_layer)
source_map[next(item.collection for item in settings.groups
                if item.collection.name == "CM_Back")].exclude = True
layer_state = capture_scene_state(bpy.context)
temp_layer = _create_view_layer(bpy.context)
assert collection_layer_map(temp_layer)[next(item.collection for item in settings.groups
                                             if item.collection.name == "CM_Back")].exclude
_remove_view_layer(bpy.context, temp_layer)
assert not restore_scene_state(bpy.context, layer_state)
source_map[next(item.collection for item in settings.groups
                if item.collection.name == "CM_Back")].exclude = False
assert user_named_layer.get("sentinel") == "keep"

back.hide_render = True
hidden_path = str(output / "hidden-object-id.png")
render_color_id(bpy.context, hidden_path)
hidden_alpha = alpha_range(hidden_path)
assert back.hide_render is True
back.hide_render = False

id_path = color_id_path(scene, settings)
render_color_id(bpy.context, id_path)
assert os.path.isfile(id_path) and os.path.getsize(id_path) > 100
id_alpha = alpha_range(id_path)
assert id_alpha[1] > 0.99 and id_alpha[0] < 0.01
assert id_alpha[2] > hidden_alpha[2] + 5.0
assert max(opaque_color_spread(id_path)) > 0.25
print("PASS color ID render", id_path)

target = next(item for item in settings.groups if item.collection.name == "CM_Back")
settings.mask_output_mode = "VISIBLE"
visible_path = mask_path(scene, settings, target.collection.name)
render_mask(bpy.context, target, visible_path)
assert os.path.isfile(visible_path) and os.path.getsize(visible_path) > 100
assert pathlib.Path(visible_path).stem == target.collection.name
visible_alpha = alpha_range(visible_path)
assert visible_alpha[1] > 0.99 and visible_alpha[0] < 0.01
mask_rgb = closest_opaque_rgb(visible_path, target.color)
id_rgb = closest_opaque_rgb(id_path, target.color)
assert max(abs(mask_rgb[index] - id_rgb[index]) for index in range(3)) < 0.03, (
    tuple(target.color), mask_rgb, id_rgb
)
print("PASS visible mask render", visible_path)

settings.mask_output_mode = "SILHOUETTE"
silhouette_path = mask_path(scene, settings, target.collection.name)
render_mask(bpy.context, target, silhouette_path)
assert os.path.isfile(silhouette_path) and os.path.getsize(silhouette_path) > 100
silhouette_alpha = alpha_range(silhouette_path)
assert silhouette_alpha[2] > visible_alpha[2] + 5.0
print("PASS silhouette mask render", silhouette_path)

settings.mask_edge_protection = False
unprotected_path = str(output / "unprotected.png")
render_mask(bpy.context, target, unprotected_path)
unprotected_alpha = alpha_range(unprotected_path)
settings.mask_edge_protection = True
protected_path = str(output / "protected.png")
render_mask(bpy.context, target, protected_path)
protected_alpha = alpha_range(protected_path)
assert protected_alpha[2] > unprotected_alpha[2] + 1.0
print("PASS automatic one-pixel edge protection")
settings.mask_edge_protection = False

settings.mask_output_mode = "VISIBLE"
cutout_output = cutout_path(scene, settings, target.collection.name)
render_cutout(bpy.context, target, cutout_output)
cutout_alpha = alpha_range(cutout_output)
assert os.path.isfile(cutout_output) and os.path.getsize(cutout_output) > 100
assert cutout_alpha[1] > 0.99 and cutout_alpha[0] < 0.01
assert cutout_alpha[2] < silhouette_alpha[2] - 1.0
cutout_rgb = closest_opaque_rgb(cutout_output, (0.12, 0.48, 0.86, 1.0))
assert (
    cutout_rgb[2] > cutout_rgb[1] > cutout_rgb[0] and cutout_rgb[2] > 0.3
), cutout_rgb
print("PASS original-material transparent cutout", cutout_output)

front_layer = collection_layer_map(bpy.context.view_layer)[front.users_collection[0]]
front_layer.holdout = True
isolate_original = (
    front.hide_render, front.is_holdout, back.hide_render, back.is_holdout,
    scene.render.film_transparent, front_layer.holdout,
)
assert bpy.ops.cmask.isolate_object_render(
    object_name=back.name, render_now=False
) == {"FINISHED"}
assert settings.isolate_active and settings.isolate_label == back.name
assert front.is_holdout and not back.is_holdout and not back.hide_render
assert scene.render.film_transparent and front_layer.holdout
assert bpy.ops.cmask.clear_isolate_render() == {"FINISHED"}
isolate_restored = (
    front.hide_render, front.is_holdout, back.hide_render, back.is_holdout,
    scene.render.film_transparent, front_layer.holdout,
)
assert isolate_restored == isolate_original, (isolate_original, isolate_restored)
assert not settings.isolate_active
front_layer.holdout = False
print("PASS object solo-render state and exact cancellation restore")

assert bpy.ops.cmask.isolate_collection_render(
    collection_name=target.collection.name, render_now=False
) == {"FINISHED"}
assert settings.isolate_active and settings.isolate_label == target.collection.name
assert front.is_holdout and not back.is_holdout
assert bpy.ops.cmask.clear_isolate_render() == {"FINISHED"}
assert not settings.isolate_active and not front.is_holdout
print("PASS Collection solo-render state and cancellation")

empty_isolation_collection = bpy.data.collections.new("CM_EmptyIsolation")
scene.collection.children.link(empty_isolation_collection)
assert bpy.ops.cmask.isolate_object_render(
    object_name=back.name, render_now=False
) == {"FINISHED"}
try:
    bpy.ops.cmask.isolate_collection_render(
        collection_name=empty_isolation_collection.name, render_now=False
    )
except RuntimeError as exc:
    assert "no renderable objects" in str(exc)
else:
    raise AssertionError("Expected an invalid solo-render target to fail")
assert settings.isolate_active and settings.isolate_label == back.name
assert scene.render.film_transparent
assert bpy.ops.cmask.clear_isolate_render() == {"FINISHED"}
bpy.data.collections.remove(empty_isolation_collection)
print("PASS invalid solo-render target preserves the active state")

target_layer = collection_layer_map(bpy.context.view_layer)[target.collection]
target_layer.exclude = True
assert collection_layer_map(bpy.context.view_layer)[target.collection].exclude is True
original_target_name = target.collection.name
assert bpy.ops.cmask.isolate_collection_render(
    collection_name=original_target_name, render_now=False
) == {"FINISHED"}
target.collection.name = original_target_name + "_Renamed"
assert bpy.ops.cmask.clear_isolate_render() == {"FINISHED"}
target_layer = collection_layer_map(bpy.context.view_layer)[target.collection]
assert target_layer.exclude is True
target.collection.name = original_target_name
target_layer.exclude = False
print("PASS renamed Collection solo-render restoration")

completed_solo_renders = []


def record_solo_render(_scene, _depsgraph):
    completed_solo_renders.append(True)


bpy.app.handlers.render_post.append(record_solo_render)
try:
    assert bpy.ops.cmask.isolate_object_render(
        object_name=back.name, render_now=True
    ) == {"FINISHED"}
finally:
    bpy.app.handlers.render_post.remove(record_solo_render)
assert completed_solo_renders == [True]
assert bpy.ops.cmask.clear_isolate_render() == {"FINISHED"}
print("PASS immediate object solo render")

settings.mask_output_mode = "SILHOUETTE"

straight_sample = fractional_rgba(silhouette_path)
assert max(abs(straight_sample[index] - id_rgb[index])
           for index in range(3)) < 0.03
settings.alpha_mode = "PREMULTIPLIED"
premultiplied_path = str(output / "premultiplied.png")
render_mask(bpy.context, target, premultiplied_path)
premultiplied_sample = fractional_rgba(premultiplied_path)
assert max(abs(premultiplied_sample[index] -
               id_rgb[index] * premultiplied_sample[3])
           for index in range(3)) < 0.05
assert max(premultiplied_sample[:3]) < 0.9
settings.alpha_mode = "STRAIGHT"
print("PASS straight and premultiplied alpha")

transparent_material = bpy.data.materials.new("TransparentMaterial")
transparent_material.diffuse_color = (1.0, 1.0, 1.0, 0.25)
back.data.materials.clear()
back.data.materials.append(transparent_material)
settings.transparent_material_mode = "INCLUDE"
transparent_included_path = str(output / "transparent-included.png")
render_mask(bpy.context, target, transparent_included_path)
settings.transparent_material_mode = "EXCLUDE"
transparent_excluded_path = str(output / "transparent-excluded.png")
render_mask(bpy.context, target, transparent_excluded_path)
transparent_cutout_excluded_path = str(output / "transparent-cutout-excluded.png")
render_cutout(bpy.context, target, transparent_cutout_excluded_path)
assert alpha_range(transparent_included_path)[2] > 100.0
assert alpha_range(transparent_excluded_path)[2] < 0.01
assert alpha_range(transparent_cutout_excluded_path)[2] < 0.01
settings.transparent_material_mode = "INCLUDE"
back.data.materials.clear()
back.data.materials.append(original_material)
print("PASS transparent material include and exclude")

settings.edge_adjustment = 2
expanded_path = str(output / "expanded.png")
render_mask(bpy.context, target, expanded_path)
expanded_alpha = alpha_range(expanded_path)
settings.edge_adjustment = -2
contracted_path = str(output / "contracted.png")
render_mask(bpy.context, target, contracted_path)
contracted_alpha = alpha_range(contracted_path)
assert expanded_alpha[2] > silhouette_alpha[2] > contracted_alpha[2]
print("PASS edge expansion and contraction")

settings.edge_adjustment = 0
settings.output_format = "OPEN_EXR"
settings.color_depth = "32"
exr_path = mask_path(scene, settings, target.collection.name)
render_mask(bpy.context, target, exr_path)
with open(exr_path, "rb") as handle:
    assert handle.read(4) == b"\x76\x2f\x31\x01"
print("PASS 32-bit OpenEXR", exr_path)

settings.multilayer_include_color_id = True
multilayer_output = multilayer_path(scene, settings)
assert bpy.ops.cmask.export_multilayer_exr() == {"FINISHED"}
import OpenImageIO as oiio
multilayer_input = oiio.ImageInput.open(multilayer_output)
assert multilayer_input
try:
    multilayer_spec = multilayer_input.spec()
    multilayer_channels = list(multilayer_spec.channelnames)
finally:
    multilayer_input.close()
assert len(multilayer_channels) == 12
assert {name.split(".", 1)[0] for name in multilayer_channels} == {
    "Color_ID", "CM_Front", "CM_Back",
}
assert [item.name for item in settings.last_multilayer_layers] == [
    "Color_ID", "CM_Front", "CM_Back",
]
assert settings.output_format == "OPEN_EXR" and settings.color_depth == "32"
multilayer_reports = list((output / "Reports").glob("*multilayer*.json"))
assert len(multilayer_reports) == 1
with open(multilayer_reports[0], "r", encoding="utf-8") as handle:
    multilayer_report = json.load(handle)
assert multilayer_report["multilayer_layers"] == [
    "Color_ID", "CM_Front", "CM_Back",
]
print("PASS Multilayer EXR independent RGBA layers", multilayer_output)

from collection_mask_exporter.core.cryptomatte import cryptomatte_hash
settings.cryptomatte_depth = "6"
cryptomatte_output = cryptomatte_path(scene, settings)
restored_crypto_settings = (
    settings.output_format, settings.color_depth, settings.mask_output_mode,
    settings.edge_adjustment, settings.alpha_mode,
)
assert bpy.ops.cmask.export_cryptomatte() == {"FINISHED"}
cryptomatte_input = oiio.ImageInput.open(cryptomatte_output)
assert cryptomatte_input
try:
    cryptomatte_spec = cryptomatte_input.spec()
    assert list(cryptomatte_spec.channelnames) == [
        f"CryptoCollection{layer:02d}.{channel}"
        for layer in range(3) for channel in ("R", "G", "B", "A")
    ]
    metadata_id = cryptomatte_hash("CryptoCollection")[2][:-1]
    prefix = f"cryptomatte/{metadata_id}/"
    assert cryptomatte_spec.get_string_attribute(prefix + "name") == "CryptoCollection"
    crypto_manifest = json.loads(
        cryptomatte_spec.get_string_attribute(prefix + "manifest")
    )
    assert set(crypto_manifest) == {"CM_Front", "CM_Back"}
finally:
    cryptomatte_input.close()
assert os.path.isfile(cryptomatte_output)
assert restored_crypto_settings == (
    settings.output_format, settings.color_depth, settings.mask_output_mode,
    settings.edge_adjustment, settings.alpha_mode,
)
crypto_reports = list((output / "Reports").glob("*cryptomatte*.json"))
assert len(crypto_reports) == 1
print("PASS Collection Cryptomatte EXR", cryptomatte_output)

settings.output_format = "PNG"
settings.color_depth = "16"
settings.filename_template = "{scene}_{collection}_{frame}_{mode}"
settings.write_report = True
settings.create_compositor_nodes = True
settings.mask_output_mode = "VISIBLE"
settings.active_group_index = next(
    index for index, item in enumerate(settings.groups) if item == target
)
expected_16_bit = mask_path(scene, settings, target.collection.name)
assert bpy.ops.cmask.export_selected_mask() == {"FINISHED"}
with open(expected_16_bit, "rb") as handle:
    png_header = handle.read(25)
assert png_header[:8] == b"\x89PNG\r\n\x1a\n" and png_header[24] == 16
reports = list((output / "Reports").glob("*selected_mask*.json"))
assert reports
with open(reports[0], "r", encoding="utf-8") as handle:
    report = json.load(handle)
assert report["success"] is True and report["color_depth"] == "16"
assert report["alpha_mode"] == "STRAIGHT"
assert report["mask_use_group_name"] is True
assert report["mask_use_group_color"] is True
assert report["mask_edge_protection"] is False
assert report["transparent_material_mode"] == "INCLUDE"
assert expected_16_bit in report["outputs"]
assert report["create_compositor_nodes"] is True
assert len(settings.last_outputs) == 1
compositor_tree = get_compositor_tree(scene)
generated_nodes = [node for node in compositor_tree.nodes
                   if node.get("cmask_generated") and node.type == "IMAGE"]
assert len(generated_nodes) == 1
assert bpy.ops.cmask.create_compositor_nodes() == {"FINISHED"}
generated_nodes = [node for node in compositor_tree.nodes
                   if node.get("cmask_generated") and node.type == "IMAGE"]
assert len(generated_nodes) == 1
settings.create_compositor_nodes = False
print("PASS 16-bit template and JSON report", expected_16_bit)

restored = (scene.render.engine, scene.render.image_settings.file_format,
            scene.render.film_transparent, tuple(front.color), back.hide_render,
            front.is_holdout, scene.render.use_compositing,
            scene.render.use_sequencer, tuple(front.data.materials),
            tuple(back.data.materials))
assert restored == original, (original, restored)
assert user_named_layer.get("sentinel") == "keep"
assert user_named_material.node_tree.nodes.get("UserSentinel") is not None
assert not any(layer.name.startswith(TEMP_VIEW_LAYER + "_")
               for layer in scene.view_layers)
assert not any(material.name.startswith("__CMASK_MATERIAL_ID_") or
               material.name.startswith("__CMASK_MATERIAL_WHITE_") or
               material.name.startswith("__CMASK_MATERIAL_MASK_")
               for material in bpy.data.materials)
print("PASS state restoration")

# Batch mode: two cameras x two frames x (one ID + one enabled MASK).
second_camera_data = scene.camera.data.copy()
second_camera = bpy.data.objects.new("CameraBatch", second_camera_data)
scene.collection.objects.link(second_camera)
second_camera.matrix_world = scene.camera.matrix_world.copy()
for item in settings.groups:
    item.enabled = item == target
settings.output_format = "PNG"
settings.color_depth = "8"
settings.edge_adjustment = 0
settings.filename_template = "{blend}_{collection}_{mode}"
settings.camera_mode = "ALL"
settings.frame_mode = "RANGE"
settings.frame_start = 1
settings.frame_end = 2
settings.frame_step = 1
original_camera = scene.camera
original_frame = scene.frame_current
expected_batch_outputs = len([obj for obj in scene.objects if obj.type == "CAMERA"]) * 2 * 2
assert bpy.ops.cmask.export_batch() == {"FINISHED"}
batch_report_path = output / "Reports" / "untitled_batch_cmask_report.json"
with open(batch_report_path, "r", encoding="utf-8") as handle:
    batch_report = json.load(handle)
assert batch_report["success"] is True
assert len(batch_report["outputs"]) == expected_batch_outputs
assert len(set(path.lower() for path in batch_report["outputs"])) == expected_batch_outputs
assert scene.camera == original_camera and scene.frame_current == original_frame
print("PASS multi-camera frame-range batch")
print("CMASK RENDER TESTS PASSED")

addon.unregister()
