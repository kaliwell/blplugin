# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

"""Persistent solo-render state with transparent occluders."""

import bpy

from ..constants import is_renderable_object
from ..translations import iface


def _walk_layer_collections(root, path=""):
    yield path, root
    for index, child in enumerate(root.children):
        child_path = f"{path}/{index}" if path else str(index)
        yield from _walk_layer_collections(child, child_path)


def _layer_at_path(root, path):
    layer = root
    if not path:
        return layer
    for segment in path.split("/"):
        index = int(segment)
        if index >= len(layer.children):
            return None
        layer = layer.children[index]
    return layer


def clear_render_isolation(scene):
    """Restore the exact object, layer, and transparency state saved on entry."""
    settings = scene.cmask_settings
    errors = []
    for stored in settings.isolate_object_states:
        obj = stored.object or bpy.data.objects.get(stored.object_name)
        if obj is None:
            continue
        try:
            obj.hide_render = stored.hide_render
            obj.is_holdout = stored.is_holdout
        except (ReferenceError, RuntimeError) as exc:
            errors.append(f"{stored.object_name}: {exc}")
    for stored in settings.isolate_layer_states:
        view_layer = scene.view_layers.get(stored.view_layer_name)
        if view_layer is None:
            errors.append(iface("View Layer {name} no longer exists").format(
                name=stored.view_layer_name
            ))
            continue
        candidates = list(_walk_layer_collections(view_layer.layer_collection))
        pointer = stored.collection_pointer
        layer = None
        if pointer:
            layer = next(
                (candidate for _path, candidate in candidates
                 if str(candidate.collection.as_pointer()) == pointer),
                None,
            )
        if layer is None:
            layer = next(
                (candidate for _path, candidate in candidates
                 if candidate.collection.name == stored.collection_name),
                None,
            )
        if layer is None:
            layer = _layer_at_path(view_layer.layer_collection, stored.path)
            if layer is not None:
                errors.append(iface(
                    "{location}: Collection identity changed; restored by original path"
                ).format(location=f"{stored.view_layer_name}/{stored.path}"))
        if layer is None:
            errors.append(iface("{location}: Layer Collection no longer exists").format(
                location=f"{stored.view_layer_name}/{stored.path}"
            ))
            continue
        try:
            layer.exclude = stored.exclude
            layer.holdout = stored.holdout
            layer.indirect_only = stored.indirect_only
        except (ReferenceError, RuntimeError) as exc:
            errors.append(f"{stored.view_layer_name}/{stored.path}: {exc}")
    if settings.isolate_active:
        scene.render.film_transparent = settings.isolate_previous_film_transparent
    settings.isolate_object_states.clear()
    settings.isolate_layer_states.clear()
    settings.isolate_active = False
    settings.isolate_label = ""
    return errors


def _activate(scene, view_layer, targets, label):
    settings = scene.cmask_settings
    scene_objects = set(scene.objects)
    targets = {
        obj for obj in targets
        if obj in scene_objects and is_renderable_object(obj)
    }
    if not targets:
        raise ValueError(iface("The target contains no renderable objects"))
    clear_render_isolation(scene)

    settings.isolate_previous_film_transparent = scene.render.film_transparent
    settings.isolate_active = True
    settings.isolate_label = label
    try:
        for obj in scene.objects:
            if not is_renderable_object(obj):
                continue
            stored = settings.isolate_object_states.add()
            stored.object = obj
            stored.object_name = obj.name
            stored.hide_render = bool(obj.hide_render)
            stored.is_holdout = bool(obj.is_holdout)
            if obj in targets:
                obj.hide_render = False
                obj.is_holdout = False
            elif obj.hide_render:
                obj.is_holdout = False
            else:
                obj.is_holdout = True

        target_names = {obj.name for obj in targets}
        for path, layer in _walk_layer_collections(view_layer.layer_collection):
            contains_target = any(
                obj.name in target_names for obj in layer.collection.all_objects
            )
            if not contains_target:
                continue
            if not (layer.exclude or layer.holdout or layer.indirect_only):
                continue
            stored = settings.isolate_layer_states.add()
            stored.view_layer_name = view_layer.name
            stored.path = path
            stored.collection_name = layer.collection.name
            stored.collection_pointer = str(layer.collection.as_pointer())
            stored.exclude = bool(layer.exclude)
            stored.holdout = bool(layer.holdout)
            stored.indirect_only = bool(layer.indirect_only)
            layer.exclude = False
            layer.holdout = False
            layer.indirect_only = False

        scene.render.film_transparent = True
    except Exception:
        clear_render_isolation(scene)
        raise
    return len(targets)


def isolate_object(scene, view_layer, obj):
    if obj is None or obj not in set(scene.objects):
        raise ValueError(iface("The object is not linked to the current scene"))
    return _activate(scene, view_layer, {obj}, obj.name)


def isolate_collection(scene, view_layer, collection):
    if collection is None:
        raise ValueError(iface("The Collection no longer exists"))
    scene_objects = set(scene.objects)
    targets = {obj for obj in collection.all_objects if obj in scene_objects}
    return _activate(scene, view_layer, targets, collection.name)


def clear_all_scene_isolation():
    for scene in bpy.data.scenes:
        if hasattr(scene, "cmask_settings"):
            clear_render_isolation(scene)
