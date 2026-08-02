# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from ..constants import ADDON_VERSION
from ..translations import iface


class CMASK_PT_MainPanel(bpy.types.Panel):
    bl_label = "Collection Mask Exporter"
    bl_idname = "CMASK_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Collection Mask"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.cmask_settings

        version = ".".join(str(value) for value in ADDON_VERSION)
        layout.label(text=f"CMask v{version}", icon="PACKAGE")

        box = layout.box()
        box.label(text="Presets")
        box.prop_search(settings, "preset_name", settings, "presets", text="Name")
        row = box.row(align=True)
        row.operator("cmask.save_preset", icon="ADD")
        row.operator("cmask.apply_preset", icon="CHECKMARK")
        row.operator("cmask.delete_preset", text="", icon="TRASH")

        box = layout.box()
        box.label(text="Scan Settings")
        box.prop(settings, "scan_mode")
        if settings.scan_mode == "PREFIX":
            box.prop(settings, "collection_prefix")
        elif settings.scan_mode == "MANUAL":
            box.prop(settings, "manual_collection")
            row = box.row(align=True)
            row.operator("cmask.add_manual_group", icon="ADD")
            row.operator("cmask.remove_group", icon="REMOVE")
        if settings.scan_mode != "MANUAL":
            box.prop(settings, "scan_visible_only")
        box.prop(settings, "include_children")
        box.operator("cmask.scan", icon="FILE_REFRESH")

        layout.template_list("CMASK_UL_Groups", "", settings, "groups",
                             settings, "active_group_index", rows=5)
        row = layout.row(align=True)
        up = row.operator("cmask.move_group", text="Raise Priority", icon="TRIA_UP")
        up.direction = "UP"
        down = row.operator("cmask.move_group", text="Lower Priority", icon="TRIA_DOWN")
        down.direction = "DOWN"

        box = layout.box()
        box.label(text="Conflict Check")
        box.prop(settings, "conflict_mode")
        box.operator("cmask.validate", icon="CHECKMARK")
        box.operator("cmask.compatibility_report", icon="INFO")
        for issue in settings.issues[:8]:
            row = box.row()
            row.alert = issue.level == "ERROR"
            icon = "ERROR" if issue.level == "ERROR" else "INFO"
            row.label(text=f"{issue.subject}: {issue.message}", icon=icon)
        if len(settings.issues) > 8:
            box.label(text=iface("{count} more issues").format(count=len(settings.issues) - 8))

        box = layout.box()
        box.label(text="Output Settings")
        box.prop(settings, "mask_output_mode")
        box.prop(settings, "output_format")
        box.prop(settings, "color_depth")
        box.prop(settings, "edge_adjustment")
        box.prop(settings, "alpha_mode")
        box.prop(settings, "transparent_material_mode")
        box.prop(settings, "geometry_nodes_split_sources")
        box.operator("cmask.configure_geometry_nodes_split", icon="GEOMETRY_NODES")
        box.prop(settings, "dynamic_geometry_enabled")
        if settings.dynamic_geometry_enabled:
            box.prop(settings, "dynamic_attribute_name")
        box.prop(settings, "filename_template")
        box.prop(settings, "write_report")
        box.prop(settings, "create_compositor_nodes")
        box.prop(settings, "output_directory")

        batch = layout.box()
        batch.label(text="Batch Cameras and Frames")
        batch.prop(settings, "camera_mode")
        batch.prop(settings, "frame_mode")
        if settings.frame_mode == "RANGE":
            row = batch.row(align=True)
            row.prop(settings, "frame_start")
            row.prop(settings, "frame_end")
            row.prop(settings, "frame_step")
        batch.operator("cmask.export_batch", icon="RENDER_ANIMATION")

        box = layout.box()
        box.label(text="Render and Export")
        row = box.row()
        row.enabled = not settings.geometry_nodes_split_sources
        row.operator("cmask.preview_color_id", icon="RENDER_STILL")
        if settings.geometry_nodes_split_sources:
            box.label(text="Export the split GN Color ID to inspect it", icon="INFO")
        box.operator("cmask.preview_selected_mask", icon="HIDE_OFF")
        row = box.row(align=True)
        row.operator("cmask.export_color_id", icon="IMAGE_DATA")
        row.operator("cmask.export_selected_mask", icon="RENDERLAYERS")
        box.operator("cmask.export_all_masks", icon="SEQ_STRIP_DUPLICATE")
        box.operator("cmask.export_all", icon="EXPORT")
        box.prop(settings, "multilayer_include_color_id")
        box.operator("cmask.export_multilayer_exr", icon="RENDERLAYERS")
        box.prop(settings, "cryptomatte_depth")
        box.operator("cmask.export_cryptomatte", icon="FILE_IMAGE")
        row = box.row()
        row.enabled = bool(settings.last_outputs)
        row.operator("cmask.create_compositor_nodes", icon="NODETREE")
        row = box.row()
        row.enabled = bool(settings.last_outputs)
        row.operator("cmask.create_photoshop_handoff", icon="FILE_SCRIPT")
        box.prop(settings, "photoshop_create_channels")

        layout.separator()
        layout.label(text=settings.last_status,
                     icon="ERROR" if settings.issue_count else "INFO")


CLASSES = (CMASK_PT_MainPanel,)
