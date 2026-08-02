# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass

from ..constants import is_renderable_object
from .color_manager import ensure_metadata


@dataclass(frozen=True)
class ScanIssue:
    level: str
    code: str
    subject: str
    message: str


def walk_collections(root):
    for child in root.children:
        yield child
        yield from walk_collections(child)


def visible_layer_collections(view_layer):
    """Return Collections visible through at least one View Layer branch."""
    visible = set()

    def visit(layer, parent_hidden=False):
        hidden = parent_hidden or layer.exclude or layer.hide_viewport
        if not hidden:
            visible.add(layer.collection)
        for child in layer.children:
            visit(child, hidden)

    visit(view_layer.layer_collection)
    return visible


def candidate_collections(scene, mode="PREFIX", prefix="CM_",
                          visible_collections=None):
    root = scene.collection
    if mode == "TOP_LEVEL":
        candidates = list(root.children)
    elif mode == "PREFIX":
        candidates = [collection for collection in walk_collections(root)
                      if collection.name.startswith(prefix)]
    else:
        candidates = []
    if visible_collections is not None:
        candidates = [collection for collection in candidates
                      if collection in visible_collections]
    return candidates


def renderable_objects(collection, include_children=True):
    source = collection.all_objects if include_children else collection.objects
    return [obj for obj in source if is_renderable_object(obj)]


def sync_scene_items(scene, settings, view_layer=None):
    if settings.scan_mode == "MANUAL":
        candidates = [item.collection for item in settings.groups if item.collection]
    else:
        visible = None
        if settings.scan_visible_only and view_layer is not None:
            visible = visible_layer_collections(view_layer)
        candidates = candidate_collections(scene, settings.scan_mode,
                                           settings.collection_prefix, visible)
        order = {collection: index for index, collection in enumerate(candidates)}
        candidates.sort(key=lambda collection: (
            int(collection.get("cmask_priority", 1_000_000)), order[collection]
        ))
    active_collection = None
    if 0 <= settings.active_group_index < len(settings.groups):
        active_collection = settings.groups[settings.active_group_index].collection

    settings.is_syncing = True
    try:
        # Move surviving rows into their final positions first, then trim only
        # from the tail. This keeps their RNA instances stable even when an
        # earlier Collection disappears.
        for index, collection in enumerate(candidates):
            current = next(
                (position for position in range(index, len(settings.groups))
                 if settings.groups[position].collection == collection),
                None,
            )
            if current is None:
                item = settings.groups.add()
                item.collection = collection
                current = len(settings.groups) - 1
            if current != index:
                settings.groups.move(current, index)

            color = ensure_metadata(collection, index)
            enabled = bool(collection.get("cmask_enabled", True))
            role = collection.get("cmask_role", "MASK")
            if role not in {"MASK", "HOLDOUT", "OCCLUDER", "IGNORE"}:
                role = "MASK"
            item = settings.groups[index]
            item.name = collection.name
            item.enabled = enabled
            item.role = role
            item.color = color
            item.dynamic_id = max(0, int(collection.get("cmask_dynamic_id", 0)))
            collection["cmask_priority"] = index
        while len(settings.groups) > len(candidates):
            settings.groups.remove(len(settings.groups) - 1)
    finally:
        settings.is_syncing = False
    if active_collection in candidates:
        settings.active_group_index = candidates.index(active_collection)
    else:
        settings.active_group_index = min(
            settings.active_group_index, max(0, len(settings.groups) - 1)
        )
    return candidates
