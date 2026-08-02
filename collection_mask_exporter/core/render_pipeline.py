import bpy
import sys
import os
import tempfile
import uuid

from .conflict_checker import validate_groups
from .layer_collection import configure_group_layers, iter_layer_collections
from .material_override import (
    get_id_material, get_white_material, remove_temp_material,
)
from .postprocess import apply_mask_postprocess
from .state_manager import capture_scene_state, restore_scene_state
from .transparency import object_uses_transparency
from .color_id_combine import combine_color_id
from .dynamic_geometry import cleanup_dynamic_geometry, prepare_dynamic_geometry
from ..translations import iface


TEMP_VIEW_LAYER = "__CMASK_VIEW_LAYER"


class RenderPipelineError(RuntimeError):
    pass


def _prepare_scene(scene, settings):
    if not scene.camera:
        raise RenderPipelineError(iface("The scene has no active camera"))
    engines = {
        item.identifier
        for item in scene.render.bl_rna.properties["engine"].enum_items
    }
    if "BLENDER_EEVEE_NEXT" in engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = settings.output_format
    scene.render.image_settings.color_mode = "RGBA"
    if settings.output_format == "PNG":
        scene.render.image_settings.color_depth = (
            settings.color_depth if settings.color_depth in {"8", "16"} else "16"
        )
    else:
        scene.render.image_settings.color_depth = (
            settings.color_depth if settings.color_depth in {"16", "32"} else "16"
        )
    # The user's compositor may reference another View Layer or alter colors.
    # Mask exports must be raw results from the dedicated temporary layer.
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def _create_view_layer(context):
    scene = context.scene
    source = context.window.view_layer if context.window else context.view_layer
    name = f"{TEMP_VIEW_LAYER}_{uuid.uuid4().hex}"
    layer = scene.view_layers.new(name)
    source_flags = {
        item.collection: bool(item.exclude)
        for item in iter_layer_collections(source.layer_collection)
    }
    for item in iter_layer_collections(layer.layer_collection):
        item.exclude = source_flags.get(item.collection, False)
        item.holdout = False
        item.indirect_only = False
    for other in scene.view_layers:
        other.use = other == layer
    if context.window:
        context.window.view_layer = layer
    return layer


def _remove_view_layer(context, layer):
    scene = context.scene
    errors = []
    try:
        if layer and layer.name in scene.view_layers:
            layer.material_override = None
            if context.window and context.window.view_layer == layer:
                fallback = next((item for item in scene.view_layers if item != layer), None)
                if fallback:
                    context.window.view_layer = fallback
            scene.view_layers.remove(layer)
    except Exception as exc:
        errors.append(f"删除临时 View Layer: {exc}")
    return errors


def _validate(settings):
    issues, resolution = validate_groups(settings)
    errors = [issue for issue in issues if issue.level == "ERROR"]
    if errors:
        raise RenderPipelineError(errors[0].message)
    return resolution


def _configure_objects(scene, resolution, target=None, mode="VISIBLE",
                       color_id=False, original_hidden=None,
                       transparent_material_mode="INCLUDE",
                       geometry_nodes_split_sources=False):
    original_hidden = original_hidden or {}
    dependency_sources = {
        source for sources in resolution.instance_sources.values()
        for source in sources
    }
    dependency_sources.update(
        source for sources in resolution.geometry_node_sources.values()
        for source in sources
    )
    transparent_instance_sources = set()
    if transparent_material_mode == "EXCLUDE":
        for instancer, sources in resolution.instance_sources.items():
            if object_uses_transparency(instancer):
                transparent_instance_sources.update(sources)
    objects = list(scene.objects)
    scene_objects = set(objects)
    objects.extend(obj for obj in dependency_sources if obj not in scene_objects)
    split_hosts = set()
    if geometry_nodes_split_sources and target is not None:
        split_hosts = {
            host for host, sources in resolution.geometry_node_sources.items()
            if resolution.assignments.get(host) is not target and
            any(resolution.assignments.get(source) is target for source in sources)
        }
    for obj in objects:
        if obj.type in {"CAMERA", "LIGHT"}:
            continue
        if obj in dependency_sources and obj not in resolution.assignments:
            # A source Collection can remain linked to the Scene while its
            # LayerCollection is excluded. hide_render still affects copies,
            # so preserve it for the instance dependency and let the layer
            # exclusion hide the source occurrence.
            obj.hide_render = (
                obj in transparent_instance_sources or
                original_hidden.get(obj, False)
            )
            obj.is_holdout = False
            continue
        if obj in split_hosts:
            obj.hide_render = original_hidden.get(obj, False)
            obj.is_holdout = False
            continue
        item = resolution.assignments.get(obj)
        obj.is_holdout = False
        if (transparent_material_mode == "EXCLUDE" and
                object_uses_transparency(obj)):
            obj.hide_render = True
        elif item is None or not item.enabled or item.role == "IGNORE":
            obj.hide_render = True
        elif color_id:
            obj.hide_render = original_hidden.get(obj, False)
            obj.is_holdout = item.role in {"HOLDOUT", "OCCLUDER"}
        elif item == target:
            obj.hide_render = original_hidden.get(obj, False)
        elif mode == "VISIBLE":
            obj.hide_render = original_hidden.get(obj, False)
            obj.is_holdout = True
        else:
            obj.hide_render = True


def _apply_material_to_objects(resolution, material):
    """Compatibility fallback for view-layer overrides from newer blend files."""
    handled = set()
    for obj in resolution.assignments:
        data = obj.data
        if data is None or data in handled or not hasattr(data, "materials"):
            continue
        handled.add(data)
        try:
            data.materials.clear()
            data.materials.append(material)
        except RuntimeError:
            # Linked read-only data still uses the View Layer override.
            continue


def _finish_render(context, layer, state, material, had_exception,
                   dynamic_resources=None):
    errors = _remove_view_layer(context, layer)
    errors.extend(restore_scene_state(context, state))
    errors.extend(cleanup_dynamic_geometry(dynamic_resources))
    try:
        if not remove_temp_material(material):
            errors.append("临时材质仍被数据块使用，无法安全删除")
    except Exception as exc:
        errors.append(f"删除临时材质: {exc}")
    if errors:
        message = "；".join(errors)
        if had_exception:
            print(f"CMask 恢复警告：{message}")
        else:
            raise RenderPipelineError(f"渲染完成，但场景恢复不完整：{message}")


def _split_source_targets(resolution):
    targets = []
    for host, sources in resolution.geometry_node_sources.items():
        owner = resolution.assignments.get(host)
        if owner is None or owner.role != "IGNORE":
            continue
        for source in sources:
            item = resolution.assignments.get(source)
            if item and item.enabled and item.role == "MASK" and item not in targets:
                targets.append(item)
    return targets


def _render_split_color_id(context, filepath, resolution):
    scene = context.scene
    settings = scene.cmask_settings
    split_targets = _split_source_targets(resolution)
    if not split_targets:
        return None
    if not filepath:
        raise RenderPipelineError(iface(
            "Split Geometry Nodes Color ID does not support Render Result preview; export it to a file"
        ))
    targets = [
        item for item in settings.groups
        if item.enabled and item.role == "MASK" and item.collection
    ]
    original = (
        settings.mask_output_mode, settings.edge_adjustment, settings.alpha_mode,
    )
    extension = ".exr" if settings.output_format == "OPEN_EXR" else ".png"
    try:
        settings.mask_output_mode = "VISIBLE"
        settings.edge_adjustment = 0
        settings.alpha_mode = "STRAIGHT"
        with tempfile.TemporaryDirectory(prefix="cmask-geometry-split-") as temp:
            masks = []
            for index, item in enumerate(targets):
                path = os.path.join(temp, f"Mask_{index:04d}{extension}")
                render_mask(context, item, path)
                masks.append((tuple(item.color), path))
            combine_color_id(
                filepath, masks, settings.output_format, settings.color_depth
            )
    finally:
        (settings.mask_output_mode, settings.edge_adjustment,
         settings.alpha_mode) = original
    return filepath


def render_color_id(context, filepath=None, preview=False):
    scene = context.scene
    settings = scene.cmask_settings
    resolution = _validate(settings)
    if settings.geometry_nodes_split_sources:
        split_result = _render_split_color_id(context, filepath, resolution)
        if split_result is not None:
            return split_result
    instance_sources = {
        source for sources in resolution.instance_sources.values()
        for source in sources
    }
    instance_sources.update(
        source for sources in resolution.geometry_node_sources.values()
        for source in sources
    )
    state = capture_scene_state(context, instance_sources)
    original_hidden = {
        obj: bool(obj.hide_render)
        for obj in {*scene.objects, *instance_sources}
    }
    layer = None
    material = None
    dynamic_resources = None
    try:
        _prepare_scene(scene, settings)
        dynamic_resources = prepare_dynamic_geometry(
            context, resolution, settings
        )
        layer = _create_view_layer(context)
        configure_group_layers(
            layer, settings.groups, color_id=True, reset=False
        )
        _configure_objects(scene, resolution, color_id=True,
                           original_hidden=original_hidden,
                           transparent_material_mode=
                           settings.transparent_material_mode,
                           geometry_nodes_split_sources=
                           settings.geometry_nodes_split_sources)
        for obj, item in resolution.assignments.items():
            obj.color = item.color
        material = get_id_material()
        layer.material_override = material
        _apply_material_to_objects(resolution, material)
        if filepath:
            scene.render.filepath = filepath
        bpy.ops.render.render(write_still=bool(filepath) and not preview,
                              layer=layer.name)
        return filepath
    finally:
        _finish_render(context, layer, state, material,
                       had_exception=sys.exc_info()[0] is not None,
                       dynamic_resources=dynamic_resources)


def render_mask(context, target, filepath=None, preview=False):
    scene = context.scene
    settings = scene.cmask_settings
    if not target or not target.collection:
        raise RenderPipelineError(iface("No mask group is selected"))
    if not target.enabled or target.role != "MASK":
        raise RenderPipelineError(iface("Only enabled MASK groups can be exported"))
    resolution = _validate(settings)
    instance_sources = {
        source for sources in resolution.instance_sources.values()
        for source in sources
    }
    instance_sources.update(
        source for sources in resolution.geometry_node_sources.values()
        for source in sources
    )
    state = capture_scene_state(context, instance_sources)
    original_hidden = {
        obj: bool(obj.hide_render)
        for obj in {*scene.objects, *instance_sources}
    }
    layer = None
    material = None
    dynamic_resources = None
    try:
        _prepare_scene(scene, settings)
        dynamic_resources = prepare_dynamic_geometry(
            context, resolution, settings
        )
        layer = _create_view_layer(context)
        configure_group_layers(
            layer, settings.groups, target=target,
            mode=settings.mask_output_mode, reset=False,
        )
        _configure_objects(scene, resolution, target=target,
                           mode=settings.mask_output_mode,
                           original_hidden=original_hidden,
                           transparent_material_mode=
                           settings.transparent_material_mode,
                           geometry_nodes_split_sources=
                           settings.geometry_nodes_split_sources)
        material = get_white_material()
        layer.material_override = material
        _apply_material_to_objects(resolution, material)
        if filepath:
            scene.render.filepath = filepath
        bpy.ops.render.render(write_still=bool(filepath) and not preview,
                              layer=layer.name)
        apply_mask_postprocess(
            scene, filepath, settings.edge_adjustment, settings.alpha_mode,
            preview=preview,
        )
        return filepath
    finally:
        _finish_render(context, layer, state, material,
                       had_exception=sys.exc_info()[0] is not None,
                       dynamic_resources=dynamic_resources)
