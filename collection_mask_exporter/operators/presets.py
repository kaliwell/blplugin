# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from ..core.color_manager import ensure_metadata
from ..core.scanner import sync_scene_items, walk_collections
from ..translations import iface


SETTING_FIELDS = (
    "scan_mode",
    "collection_prefix",
    "include_children",
    "scan_visible_only",
    "conflict_mode",
    "mask_output_mode",
    "output_directory",
    "output_format",
    "color_depth",
    "edge_adjustment",
    "alpha_mode",
    "mask_use_group_name",
    "mask_use_group_color",
    "transparent_material_mode",
    "create_compositor_nodes",
    "photoshop_create_channels",
    "multilayer_include_color_id",
    "cryptomatte_depth",
    "geometry_nodes_split_sources",
    "dynamic_geometry_enabled",
    "dynamic_attribute_name",
    "filename_template",
    "write_report",
    "camera_mode",
    "frame_mode",
    "frame_start",
    "frame_end",
    "frame_step",
)


def _find_preset(settings, name):
    return next((preset for preset in settings.presets if preset.name == name), None)


def _scene_collections_by_uuid(scene):
    result = {}
    by_name = {}
    for collection in walk_collections(scene.collection):
        collection_uuid = collection.get("cmask_uuid", "")
        if collection_uuid:
            result[collection_uuid] = collection
        by_name.setdefault(collection.name, collection)
    return result, by_name


def _resolve_preset_groups(scene, preset):
    by_uuid, by_name = _scene_collections_by_uuid(scene)
    resolved = []
    missing = []
    used = set()
    for stored in preset.groups:
        collection = by_uuid.get(stored.collection_uuid)
        if collection is None:
            collection = by_name.get(stored.collection_name)
        if collection is None or collection in used:
            if collection is None:
                missing.append(stored.collection_name)
            continue
        used.add(collection)
        resolved.append((stored, collection))
    return resolved, missing


def _apply_group_style(settings, item, stored, collection, priority):
    ensure_metadata(collection, priority)
    collection["cmask_priority"] = priority
    collection["cmask_enabled"] = bool(stored.enabled)
    collection["cmask_role"] = stored.role
    collection["cmask_color"] = list(stored.color)
    collection["cmask_dynamic_id"] = int(stored.dynamic_id)
    item.collection = collection
    item.name = collection.name
    item.enabled = stored.enabled
    item.role = stored.role
    item.color = stored.color
    item.dynamic_id = stored.dynamic_id


class CMASK_OT_SavePreset(bpy.types.Operator):
    bl_idname = "cmask.save_preset"
    bl_label = "Save Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.cmask_settings
        name = settings.preset_name.strip()
        if not name:
            self.report({"ERROR"}, iface("Preset name cannot be empty"))
            return {"CANCELLED"}
        preset = _find_preset(settings, name)
        if preset is None:
            preset = settings.presets.add()
            preset.name = name
        for field in SETTING_FIELDS:
            value = getattr(settings, field)
            if field == "output_directory":
                value = bpy.path.abspath(value)
            setattr(preset, field, value)
        preset.groups.clear()
        for index, item in enumerate(settings.groups):
            collection = item.collection
            if not collection:
                continue
            ensure_metadata(collection, index)
            stored = preset.groups.add()
            stored.collection_uuid = collection["cmask_uuid"]
            stored.collection_name = collection.name
            stored.enabled = item.enabled
            stored.role = item.role
            stored.color = item.color
            stored.dynamic_id = item.dynamic_id
        settings.last_status = iface("Preset saved: {name}").format(name=name)
        self.report({"INFO"}, settings.last_status)
        return {"FINISHED"}


class CMASK_OT_ApplyPreset(bpy.types.Operator):
    bl_idname = "cmask.apply_preset"
    bl_label = "Apply Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        settings = scene.cmask_settings
        preset = _find_preset(settings, settings.preset_name.strip())
        if preset is None:
            self.report({"ERROR"}, iface("The specified preset was not found"))
            return {"CANCELLED"}

        for field in SETTING_FIELDS:
            setattr(settings, field, getattr(preset, field))
        resolved, missing = _resolve_preset_groups(scene, preset)
        for priority, (_stored, collection) in enumerate(resolved):
            collection["cmask_priority"] = priority

        if settings.scan_mode == "MANUAL":
            settings.is_syncing = True
            try:
                settings.groups.clear()
                for priority, (stored, collection) in enumerate(resolved):
                    item = settings.groups.add()
                    _apply_group_style(settings, item, stored, collection, priority)
            finally:
                settings.is_syncing = False
        else:
            sync_scene_items(scene, settings, context.view_layer)
            stored_by_collection = {
                collection: stored for stored, collection in resolved
            }
            settings.is_syncing = True
            try:
                for priority, item in enumerate(settings.groups):
                    collection = item.collection
                    stored = stored_by_collection.get(collection)
                    if stored:
                        _apply_group_style(
                            settings, item, stored, collection, priority
                        )
            finally:
                settings.is_syncing = False

        settings.active_group_index = min(
            settings.active_group_index, max(0, len(settings.groups) - 1)
        )
        suffix = iface("; {count} Collections missing").format(count=len(missing)) if missing else ""
        settings.last_status = iface("Preset applied: {name}{suffix}").format(
            name=preset.name, suffix=suffix
        )
        self.report({"WARNING"} if missing else {"INFO"}, settings.last_status)
        return {"FINISHED"}


class CMASK_OT_DeletePreset(bpy.types.Operator):
    bl_idname = "cmask.delete_preset"
    bl_label = "Delete Preset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.cmask_settings
        name = settings.preset_name.strip()
        index = next(
            (index for index, preset in enumerate(settings.presets)
             if preset.name == name),
            None,
        )
        if index is None:
            self.report({"ERROR"}, iface("The specified preset was not found"))
            return {"CANCELLED"}
        settings.presets.remove(index)
        settings.preset_name = (
            settings.presets[min(index, len(settings.presets) - 1)].name
            if settings.presets else iface("Default Preset")
        )
        settings.last_status = iface("Preset deleted: {name}").format(name=name)
        self.report({"INFO"}, settings.last_status)
        return {"FINISHED"}


CLASSES = (CMASK_OT_SavePreset, CMASK_OT_ApplyPreset, CMASK_OT_DeletePreset)
