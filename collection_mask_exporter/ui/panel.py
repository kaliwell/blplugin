# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from ..constants import ADDON_VERSION
from ..translations import iface


class _CMASK_PT_Base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Collection Mask"

    @staticmethod
    def settings(context):
        return context.scene.cmask_settings


class CMASK_PT_MainPanel(_CMASK_PT_Base, bpy.types.Panel):
    bl_label = "Collection Mask Exporter"
    bl_idname = "CMASK_PT_main"

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        version = ".".join(str(value) for value in ADDON_VERSION)
        layout.label(text=f"CMask v{version}", icon="PACKAGE")
        layout.label(
            text=settings.last_status,
            icon="ERROR" if settings.issue_count else "INFO",
        )
        if settings.isolate_active:
            box = layout.box()
            box.alert = True
            box.label(
                text=iface("Solo render active: {name}").format(
                    name=settings.isolate_label
                ),
                icon="RESTRICT_RENDER_OFF",
            )
            box.operator("cmask.clear_isolate_render", icon="LOOP_BACK")


class _CMASK_PT_Child(_CMASK_PT_Base):
    bl_parent_id = CMASK_PT_MainPanel.bl_idname


class CMASK_PT_Presets(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "Presets"
    bl_idname = "CMASK_PT_presets"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        layout.prop_search(settings, "preset_name", settings, "presets", text="Name")
        row = layout.row(align=True)
        row.operator("cmask.save_preset", icon="ADD")
        row.operator("cmask.apply_preset", icon="CHECKMARK")
        row.operator("cmask.delete_preset", text="", icon="TRASH")


class CMASK_PT_ScanGroups(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "Scan and Groups"
    bl_idname = "CMASK_PT_scan_groups"

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        layout.prop(settings, "scan_mode")
        if settings.scan_mode == "PREFIX":
            layout.prop(settings, "collection_prefix")
        elif settings.scan_mode == "MANUAL":
            layout.prop(settings, "manual_collection")
            row = layout.row(align=True)
            row.operator("cmask.add_manual_group", icon="ADD")
            row.operator("cmask.remove_group", icon="REMOVE")
        if settings.scan_mode != "MANUAL":
            layout.prop(settings, "scan_visible_only")
        layout.prop(settings, "include_children")
        layout.operator("cmask.scan", icon="FILE_REFRESH")
        layout.template_list(
            "CMASK_UL_Groups",
            "",
            settings,
            "groups",
            settings,
            "active_group_index",
            rows=5,
        )
        row = layout.row(align=True)
        up = row.operator("cmask.move_group", text="Raise Priority", icon="TRIA_UP")
        up.direction = "UP"
        down = row.operator("cmask.move_group", text="Lower Priority", icon="TRIA_DOWN")
        down.direction = "DOWN"
        row = layout.row(align=True)
        row.operator("cmask.isolate_collection_render", icon="RENDER_STILL")
        if settings.isolate_active:
            row.operator("cmask.clear_isolate_render", icon="LOOP_BACK")


class CMASK_PT_Validation(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "Validation"
    bl_idname = "CMASK_PT_validation"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        layout.prop(settings, "conflict_mode")
        layout.operator("cmask.validate", icon="CHECKMARK")
        layout.operator("cmask.compatibility_report", icon="INFO")
        for issue in settings.issues[:8]:
            row = layout.row()
            row.alert = issue.level == "ERROR"
            icon = "ERROR" if issue.level == "ERROR" else "INFO"
            row.label(text=f"{issue.subject}: {issue.message}", icon=icon)
        if len(settings.issues) > 8:
            layout.label(
                text=iface("{count} more issues").format(
                    count=len(settings.issues) - 8
                )
            )


class CMASK_PT_OutputSettings(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "Output Settings"
    bl_idname = "CMASK_PT_output_settings"

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        layout.prop(settings, "mask_output_mode")
        layout.prop(settings, "output_format")
        layout.prop(settings, "color_depth")
        layout.prop(settings, "edge_adjustment")
        layout.prop(settings, "mask_edge_protection")
        layout.prop(settings, "alpha_mode")
        layout.prop(settings, "mask_use_group_name")
        layout.prop(settings, "mask_use_group_color")
        layout.prop(settings, "transparent_material_mode")
        layout.prop(settings, "filename_template")
        layout.prop(settings, "write_report")
        layout.prop(settings, "output_directory")


class CMASK_PT_GeometryNodes(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "Geometry Nodes Settings"
    bl_idname = "CMASK_PT_geometry_nodes"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        layout.prop(settings, "geometry_nodes_split_sources")
        layout.operator("cmask.configure_geometry_nodes_split", icon="GEOMETRY_NODES")
        layout.prop(settings, "dynamic_geometry_enabled")
        if settings.dynamic_geometry_enabled:
            layout.prop(settings, "dynamic_attribute_name")


class CMASK_PT_Batch(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "Batch Cameras and Frames"
    bl_idname = "CMASK_PT_batch"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        layout.prop(settings, "camera_mode")
        layout.prop(settings, "frame_mode")
        if settings.frame_mode == "RANGE":
            row = layout.row(align=True)
            row.prop(settings, "frame_start")
            row.prop(settings, "frame_end")
            row.prop(settings, "frame_step")
        layout.operator("cmask.export_batch", icon="RENDER_ANIMATION")


class CMASK_PT_Delivery(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "One-Click Delivery"
    bl_idname = "CMASK_PT_delivery"

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        layout.operator("cmask.export_delivery", icon="RENDER_STILL")
        layout.prop(settings, "delivery_include_cutouts")
        layout.prop(settings, "photoshop_create_channels")
        row = layout.row()
        row.enabled = bool(settings.last_outputs)
        row.operator("cmask.create_photoshop_handoff", icon="FILE_SCRIPT")


class CMASK_PT_IndividualExports(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "Individual Exports"
    bl_idname = "CMASK_PT_individual_exports"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        row = layout.row()
        row.enabled = not settings.geometry_nodes_split_sources
        row.operator("cmask.preview_color_id", icon="RENDER_STILL")
        if settings.geometry_nodes_split_sources:
            layout.label(text="Export the split GN Color ID to inspect it", icon="INFO")
        layout.operator("cmask.preview_selected_mask", icon="HIDE_OFF")
        row = layout.row(align=True)
        row.operator("cmask.export_color_id", icon="IMAGE_DATA")
        row.operator("cmask.export_selected_mask", icon="RENDERLAYERS")
        layout.operator("cmask.export_all_masks", icon="SEQ_STRIP_DUPLICATE")
        row = layout.row(align=True)
        row.operator("cmask.export_selected_cutout", icon="IMAGE_ALPHA")
        row.operator("cmask.export_all_cutouts", icon="SEQ_STRIP_DUPLICATE")
        layout.operator("cmask.export_all", icon="EXPORT")


class CMASK_PT_AdvancedOutput(_CMASK_PT_Child, bpy.types.Panel):
    bl_label = "Advanced Output"
    bl_idname = "CMASK_PT_advanced_output"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = self.settings(context)
        layout.prop(settings, "multilayer_include_color_id")
        layout.operator("cmask.export_multilayer_exr", icon="RENDERLAYERS")
        layout.prop(settings, "cryptomatte_depth")
        layout.operator("cmask.export_cryptomatte", icon="FILE_IMAGE")
        layout.prop(settings, "create_compositor_nodes")
        row = layout.row()
        row.enabled = bool(settings.last_outputs)
        row.operator("cmask.create_compositor_nodes", icon="NODETREE")


CLASSES = (
    CMASK_PT_MainPanel,
    CMASK_PT_Presets,
    CMASK_PT_ScanGroups,
    CMASK_PT_Validation,
    CMASK_PT_OutputSettings,
    CMASK_PT_GeometryNodes,
    CMASK_PT_Batch,
    CMASK_PT_Delivery,
    CMASK_PT_IndividualExports,
    CMASK_PT_AdvancedOutput,
)
