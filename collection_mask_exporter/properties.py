# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.props import (
    BoolProperty, CollectionProperty, EnumProperty, FloatVectorProperty,
    IntProperty, PointerProperty, StringProperty,
)
from bpy.types import PropertyGroup

from .constants import COLLECTION_ROLES


def _sync_item_to_collection(item, _context):
    collection = item.collection
    if not collection:
        return
    owner = item.id_data
    settings = getattr(owner, "cmask_settings", None)
    if settings and settings.is_syncing:
        return
    collection["cmask_enabled"] = bool(item.enabled)
    collection["cmask_role"] = item.role
    collection["cmask_color"] = list(item.color)
    collection["cmask_dynamic_id"] = int(item.dynamic_id)


class CMASK_PG_GroupItem(PropertyGroup):
    collection: PointerProperty(type=bpy.types.Collection)
    enabled: BoolProperty(name="Enabled", default=True, update=_sync_item_to_collection)
    role: EnumProperty(name="Role", items=COLLECTION_ROLES, default="MASK",
                       update=_sync_item_to_collection)
    color: FloatVectorProperty(name="Color", subtype="COLOR", size=4,
                               min=0.0, max=1.0, default=(1, 0, 0, 1),
                               update=_sync_item_to_collection)
    dynamic_id: IntProperty(name="Dynamic GN ID", default=0, min=0,
                            update=_sync_item_to_collection)


class CMASK_PG_Issue(PropertyGroup):
    level: StringProperty()
    code: StringProperty()
    subject: StringProperty()
    message: StringProperty()


class CMASK_PG_OutputFile(PropertyGroup):
    path: StringProperty()


class CMASK_PG_PresetGroup(PropertyGroup):
    collection_uuid: StringProperty()
    collection_name: StringProperty()
    enabled: BoolProperty(default=True)
    role: StringProperty(default="MASK")
    color: FloatVectorProperty(size=4, min=0.0, max=1.0,
                               default=(1, 0, 0, 1))
    dynamic_id: IntProperty(default=0, min=0)


class CMASK_PG_Preset(PropertyGroup):
    scan_mode: StringProperty(default="PREFIX")
    collection_prefix: StringProperty(default="CM_")
    include_children: BoolProperty(default=True)
    scan_visible_only: BoolProperty(default=False)
    conflict_mode: StringProperty(default="PRIORITY")
    mask_output_mode: StringProperty(default="VISIBLE")
    output_directory: StringProperty(default="//CMask_Output/", subtype="DIR_PATH")
    output_format: StringProperty(default="PNG")
    color_depth: StringProperty(default="8")
    edge_adjustment: IntProperty(default=0)
    alpha_mode: StringProperty(default="STRAIGHT")
    transparent_material_mode: StringProperty(default="INCLUDE")
    create_compositor_nodes: BoolProperty(default=False)
    photoshop_create_channels: BoolProperty(default=True)
    multilayer_include_color_id: BoolProperty(default=True)
    cryptomatte_depth: StringProperty(default="6")
    geometry_nodes_split_sources: BoolProperty(default=False)
    dynamic_geometry_enabled: BoolProperty(default=False)
    dynamic_attribute_name: StringProperty(default="cmask_id")
    filename_template: StringProperty(default="{blend}_{collection}_{mode}")
    write_report: BoolProperty(default=True)
    camera_mode: StringProperty(default="CURRENT")
    frame_mode: StringProperty(default="CURRENT")
    frame_start: IntProperty(default=1)
    frame_end: IntProperty(default=250)
    frame_step: IntProperty(default=1)
    groups: CollectionProperty(type=CMASK_PG_PresetGroup)


class CMASK_PG_Settings(PropertyGroup):
    is_syncing: BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})
    scan_mode: EnumProperty(
        name="Scan Mode",
        items=(("PREFIX", "Name Prefix", "Recursively scan the specified prefix"),
               ("TOP_LEVEL", "Top-level Collections", "Scan direct children of the Scene Collection"),
               ("MANUAL", "Manual", "Use only manually added Collections")),
        default="PREFIX",
    )
    collection_prefix: StringProperty(name="Prefix", default="CM_")
    include_children: BoolProperty(name="Include Child Collections", default=True)
    scan_visible_only: BoolProperty(
        name="Only Scan Visible Collections",
        default=False,
        description="Ignore Collections excluded or hidden in the current View Layer",
    )
    conflict_mode: EnumProperty(
        name="Conflict Rule",
        items=(("PRIORITY", "Resolve by Priority", "The first item in the list wins"),
               ("STRICT", "Strict Error", "Block export when membership overlaps")),
        default="PRIORITY",
    )
    mask_output_mode: EnumProperty(
        name="Mask Mode",
        items=(("VISIBLE", "Visible Area", "Preserve real occlusion"),
               ("SILHOUETTE", "Full Silhouette", "Ignore occlusion from other groups")),
        default="VISIBLE",
    )
    output_directory: StringProperty(name="Output Directory", subtype="DIR_PATH",
                                     default="//CMask_Output/")
    manual_collection: PointerProperty(name="Collection", type=bpy.types.Collection)
    color_depth: EnumProperty(
        name="Bit Depth",
        items=(("8", "8 bit", "Suitable for color IDs and regular masks"),
               ("16", "16 bit", "High precision PNG or half-float EXR"),
               ("32", "32 bit", "Full-float OpenEXR")),
        default="8",
    )
    output_format: EnumProperty(
        name="Format",
        items=(("PNG", "PNG", "RGBA PNG"),
               ("OPEN_EXR", "OpenEXR", "RGBA OpenEXR")),
        default="PNG",
    )
    edge_adjustment: IntProperty(
        name="Edge Expand/Contract", default=0, min=-32, max=32,
        description="Positive expands Alpha; negative contracts Alpha, in pixels",
    )
    alpha_mode: EnumProperty(
        name="Alpha Storage",
        items=(("STRAIGHT", "Straight", "Keep white RGB with independent Alpha"),
               ("PREMULTIPLIED", "Premultiplied", "Multiply RGB by Alpha")),
        default="STRAIGHT",
    )
    transparent_material_mode: EnumProperty(
        name="Transparent Materials",
        items=(("INCLUDE", "Treat as Solid", "Ignore original material transparency and export full geometry"),
               ("EXCLUDE", "Exclude Object", "Exclude an entire object when a transparent material is detected")),
        default="INCLUDE",
    )
    filename_template: StringProperty(
        name="Filename Template", default="{blend}_{collection}_{mode}",
        description="Supports blend, scene, camera, collection, frame and mode",
    )
    write_report: BoolProperty(name="Write JSON Report", default=True)
    create_compositor_nodes: BoolProperty(
        name="Create Compositor Nodes After Export", default=False,
        description="Add recent outputs as Image nodes in a dedicated CMask frame",
    )
    photoshop_create_channels: BoolProperty(
        name="Create Photoshop Alpha Channels",
        default=True,
        description="Create a matching Photoshop Alpha channel for each mask output",
    )
    multilayer_include_color_id: BoolProperty(
        name="Include Color ID in Multilayer EXR", default=True,
    )
    cryptomatte_depth: EnumProperty(
        name="Cryptomatte Depth",
        items=tuple(
            (str(value), str(value), f"每像素最多保存 {value} 个 Collection")
            for value in (2, 4, 6, 8, 10, 12)
        ),
        default="6",
    )
    geometry_nodes_split_sources: BoolProperty(
        name="Split Static Geometry Nodes Sources",
        default=False,
        description="Allow explicit MASK groups referenced by an IGNORE host to export independently",
    )
    dynamic_geometry_enabled: BoolProperty(
        name="Enable Dynamic GN Attribute", default=False,
        description="Read evaluated Geometry Nodes semantics from an integer attribute",
    )
    dynamic_attribute_name: StringProperty(
        name="Dynamic Attribute", default="cmask_id",
        description="Integer attribute written by Geometry Nodes, normally cmask_id",
    )
    camera_mode: EnumProperty(
        name="Camera",
        items=(("CURRENT", "Current Camera", "Use only the active camera"),
               ("ALL", "All Cameras", "Iterate over every camera in the current scene")),
        default="CURRENT",
    )
    frame_mode: EnumProperty(
        name="Frames",
        items=(("CURRENT", "Current Frame", "Export only the current frame"),
               ("RANGE", "Frame Range", "Export a custom start, end and step range")),
        default="CURRENT",
    )
    frame_start: IntProperty(name="Start", default=1, min=-1048574, max=1048574)
    frame_end: IntProperty(name="End", default=250, min=-1048574, max=1048574)
    frame_step: IntProperty(name="Step", default=1, min=1, max=1048574)
    preset_name: StringProperty(name="Preset Name", default="Default Preset")
    presets: CollectionProperty(type=CMASK_PG_Preset)
    active_preset_index: IntProperty(default=0)
    last_outputs: CollectionProperty(type=CMASK_PG_OutputFile)
    last_multilayer_layers: CollectionProperty(type=CMASK_PG_OutputFile)
    groups: CollectionProperty(type=CMASK_PG_GroupItem)
    issues: CollectionProperty(type=CMASK_PG_Issue)
    active_group_index: IntProperty(default=0)
    last_status: StringProperty(name="Status", default="Not scanned yet")
    last_diagnostic_report: StringProperty(default="", options={"HIDDEN"})
    issue_count: IntProperty(default=0)


CLASSES = (
    CMASK_PG_GroupItem,
    CMASK_PG_Issue,
    CMASK_PG_OutputFile,
    CMASK_PG_PresetGroup,
    CMASK_PG_Preset,
    CMASK_PG_Settings,
)


def register_properties():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cmask_settings = PointerProperty(type=CMASK_PG_Settings)


def unregister_properties():
    del bpy.types.Scene.cmask_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
