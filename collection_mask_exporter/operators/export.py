# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import time
import os
import tempfile

from ..core.output_manager import (
    color_id_path, cryptomatte_path, disambiguate_path, mask_path, multilayer_path,
    unique_mask_paths,
)
from ..core.render_pipeline import RenderPipelineError, render_color_id, render_mask
from ..core.report_manager import write_export_report
from ..core.compositor import create_compositor_image_nodes
from ..core.multilayer import combine_multilayer_exr
from ..core.cryptomatte import combine_collection_cryptomatte
from ..translations import iface


class _CMaskRenderOperator:
    report_operation = None

    def run_guarded(self, context, callback):
        started = time.perf_counter()
        self._partial_outputs = []
        try:
            result = callback()
            message, outputs = result if isinstance(result, tuple) else (result, [])
            settings = context.scene.cmask_settings
            if outputs:
                settings.last_outputs.clear()
                for path in outputs:
                    item = settings.last_outputs.add()
                    item.path = path
            if settings.write_report and self.report_operation and outputs:
                try:
                    report = write_export_report(
                        context.scene, settings, self.report_operation, outputs,
                        time.perf_counter() - started,
                    )
                    message = iface("{message}; report: {report}").format(message=message, report=report)
                except (OSError, ValueError, RuntimeError) as exc:
                    self.report({"WARNING"}, iface("Export succeeded, but writing the report failed: {error}").format(error=exc))
            if settings.create_compositor_nodes and outputs:
                try:
                    nodes = create_compositor_image_nodes(context.scene, outputs)
                    message = iface("{message}; created {count} compositor image nodes").format(message=message, count=len(nodes))
                except Exception as exc:
                    self.report({"WARNING"}, iface("Export succeeded, but creating compositor nodes failed: {error}").format(error=exc))
            settings.last_status = message
            self.report({"INFO"}, message)
            return {"FINISHED"}
        except (RenderPipelineError, OSError, RuntimeError, TypeError, ValueError) as exc:
            message = str(exc)
            settings = context.scene.cmask_settings
            settings.last_status = iface("Failed: {error}").format(error=message)
            if settings.write_report and self.report_operation:
                try:
                    write_export_report(
                        context.scene, settings, self.report_operation,
                        self._partial_outputs,
                        time.perf_counter() - started, success=False, error=message,
                    )
                except Exception:
                    pass
            self.report({"ERROR"}, message)
            return {"CANCELLED"}


class CMASK_OT_CreateCompositorNodes(bpy.types.Operator):
    bl_idname = "cmask.create_compositor_nodes"
    bl_label = "Load Recent Outputs into Compositor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        paths = [item.path for item in context.scene.cmask_settings.last_outputs]
        try:
            nodes = create_compositor_image_nodes(context.scene, paths)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        message = iface("Created {count} CMask compositor image nodes").format(count=len(nodes))
        context.scene.cmask_settings.last_status = message
        self.report({"INFO"}, message)
        return {"FINISHED"}


class CMASK_OT_PreviewColorID(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.preview_color_id"
    bl_label = "Preview Color ID"

    def execute(self, context):
        return self.run_guarded(context, lambda: (
            render_color_id(context, preview=True), iface("Color ID rendered to Render Result")
        )[1])


class CMASK_OT_ExportColorID(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.export_color_id"
    bl_label = "Export Color ID"
    report_operation = "color_id"

    def execute(self, context):
        def export():
            path = color_id_path(context.scene, context.scene.cmask_settings)
            render_color_id(context, path)
            return iface("Exported: {path}").format(path=path), [path]
        return self.run_guarded(context, export)


def active_group(settings):
    index = settings.active_group_index
    return settings.groups[index] if 0 <= index < len(settings.groups) else None


class CMASK_OT_ExportSelectedMask(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.export_selected_mask"
    bl_label = "Export Selected Mask"
    report_operation = "selected_mask"

    def execute(self, context):
        settings = context.scene.cmask_settings
        target = active_group(settings)
        def export():
            name = target.collection.name if target and target.collection else "mask"
            path = mask_path(context.scene, settings, name)
            render_mask(context, target, path)
            return iface("Exported: {path}").format(path=path), [path]
        return self.run_guarded(context, export)


class CMASK_OT_PreviewSelectedMask(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.preview_selected_mask"
    bl_label = "Preview Selected Mask"

    def execute(self, context):
        target = active_group(context.scene.cmask_settings)
        return self.run_guarded(context, lambda: (
            render_mask(context, target, preview=True),
            iface("Selected group mask rendered to Render Result"),
        )[1])


class CMASK_OT_ExportAllMasks(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.export_all_masks"
    bl_label = "Export All Masks"
    report_operation = "all_masks"

    def execute(self, context):
        settings = context.scene.cmask_settings

        def export_all():
            targets = [item for item in settings.groups
                       if item.enabled and item.role == "MASK" and item.collection]
            if not targets:
                raise RenderPipelineError(iface("No MASK group is available for export"))
            outputs = []
            for item, path in unique_mask_paths(context.scene, settings, targets):
                render_mask(context, item, path)
                outputs.append(path)
            return iface("Exported {count} masks").format(count=len(targets)), outputs

        return self.run_guarded(context, export_all)


class CMASK_OT_ExportAll(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.export_all"
    bl_label = "Export All"
    report_operation = "all"

    def execute(self, context):
        settings = context.scene.cmask_settings

        def export_all():
            id_path = color_id_path(context.scene, settings)
            render_color_id(context, id_path)
            outputs = [id_path]
            targets = [item for item in settings.groups
                       if item.enabled and item.role == "MASK" and item.collection]
            for item, path in unique_mask_paths(context.scene, settings, targets):
                render_mask(context, item, path)
                outputs.append(path)
            return iface("Exported the Color ID and {count} masks").format(count=len(targets)), outputs

        return self.run_guarded(context, export_all)


class CMASK_OT_ExportMultilayerEXR(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.export_multilayer_exr"
    bl_label = "Export Multilayer EXR"
    report_operation = "multilayer"

    def execute(self, context):
        scene = context.scene
        settings = scene.cmask_settings

        def export_multilayer():
            targets = [item for item in settings.groups
                       if item.enabled and item.role == "MASK" and item.collection]
            if not targets:
                raise RenderPipelineError(iface("No MASK group is available for Multilayer EXR"))
            final_path = multilayer_path(scene, settings)
            original_format = settings.output_format
            original_depth = settings.color_depth
            settings.last_multilayer_layers.clear()
            try:
                settings.output_format = "OPEN_EXR"
                settings.color_depth = "32" if original_depth == "32" else "16"
                with tempfile.TemporaryDirectory(prefix="cmask-multilayer-") as temp:
                    layers = []
                    if settings.multilayer_include_color_id:
                        path = os.path.join(temp, "Color_ID.exr")
                        render_color_id(context, path)
                        layers.append(("Color_ID", path))
                    for index, item in enumerate(targets):
                        path = os.path.join(temp, f"Mask_{index:04d}.exr")
                        render_mask(context, item, path)
                        layers.append((item.collection.name, path))
                    resolved = combine_multilayer_exr(
                        final_path, layers, half_float=original_depth != "32"
                    )
            finally:
                settings.output_format = original_format
                settings.color_depth = original_depth

            for name, _path in resolved:
                layer = settings.last_multilayer_layers.add()
                layer.name = name
            self._partial_outputs = [final_path]
            return iface("Exported {count} Multilayer EXR layers: {path}").format(count=len(resolved), path=final_path), [final_path]

        return self.run_guarded(context, export_multilayer)


class CMASK_OT_ExportCryptomatte(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.export_cryptomatte"
    bl_label = "Export Collection Cryptomatte"
    bl_description = "Export a standard 32-bit Collection-level Cryptomatte EXR"
    report_operation = "cryptomatte"

    def execute(self, context):
        scene = context.scene
        settings = scene.cmask_settings

        def export_cryptomatte():
            targets = [item for item in settings.groups
                       if item.enabled and item.role == "MASK" and item.collection]
            if not targets:
                raise RenderPipelineError(iface("No MASK group is available for Cryptomatte"))
            final_path = cryptomatte_path(scene, settings)
            original = (
                settings.output_format, settings.color_depth,
                settings.mask_output_mode, settings.edge_adjustment,
                settings.alpha_mode,
            )
            try:
                settings.output_format = "OPEN_EXR"
                settings.color_depth = "32"
                settings.mask_output_mode = "VISIBLE"
                settings.edge_adjustment = 0
                settings.alpha_mode = "STRAIGHT"
                with tempfile.TemporaryDirectory(prefix="cmask-cryptomatte-") as temp:
                    masks = []
                    for index, item in enumerate(targets):
                        path = os.path.join(temp, f"Mask_{index:04d}.exr")
                        render_mask(context, item, path)
                        masks.append((item.collection.name, path))
                    manifest = combine_collection_cryptomatte(
                        final_path, masks, depth=int(settings.cryptomatte_depth)
                    )
            finally:
                (settings.output_format, settings.color_depth,
                 settings.mask_output_mode, settings.edge_adjustment,
                 settings.alpha_mode) = original
            self._partial_outputs = [final_path]
            return iface("Exported Cryptomatte for {count} Collections: {path}").format(
                count=len(manifest), path=final_path
            ), [final_path]

        return self.run_guarded(context, export_cryptomatte)


class CMASK_OT_ExportBatch(_CMaskRenderOperator, bpy.types.Operator):
    bl_idname = "cmask.export_batch"
    bl_label = "Batch Camera / Frame Export"
    report_operation = "batch"

    def execute(self, context):
        scene = context.scene
        settings = scene.cmask_settings

        def export_batch():
            cameras = ([scene.camera] if settings.camera_mode == "CURRENT" else
                       [obj for obj in scene.objects if obj.type == "CAMERA"])
            cameras = [camera for camera in cameras if camera]
            if not cameras:
                raise RenderPipelineError(iface("No camera is available for batch export"))
            if settings.frame_mode == "CURRENT":
                frames = [scene.frame_current]
            else:
                if settings.frame_end < settings.frame_start:
                    raise RenderPipelineError(iface("The end frame cannot be earlier than the start frame"))
                frames = range(settings.frame_start, settings.frame_end + 1,
                               settings.frame_step)
            targets = [item for item in settings.groups
                       if item.enabled and item.role == "MASK" and item.collection]
            original_camera = scene.camera
            original_camera_name = original_camera.name if original_camera else ""
            original_camera_pointer = (
                original_camera.as_pointer() if original_camera else 0
            )
            original_frame = scene.frame_current
            used = set()
            outputs = []
            self._partial_outputs = outputs
            try:
                for camera in cameras:
                    scene.camera = camera
                    for frame in frames:
                        scene.frame_set(frame)
                        suffix = f"{camera.name}_{frame:04d}"
                        id_path = disambiguate_path(
                            color_id_path(scene, settings), used, suffix
                        )
                        render_color_id(context, id_path)
                        outputs.append(id_path)
                        for item in targets:
                            path = disambiguate_path(
                                mask_path(scene, settings, item.collection.name),
                                used, suffix,
                            )
                            render_mask(context, item, path)
                            outputs.append(path)
            finally:
                restored_camera = scene.objects.get(original_camera_name)
                if (restored_camera and
                        restored_camera.as_pointer() == original_camera_pointer):
                    scene.camera = restored_camera
                elif not original_camera_name:
                    scene.camera = None
                scene.frame_set(original_frame)
            return iface(
                "Batch export complete: {cameras} cameras, {frames} frame positions, {files} files"
            ).format(cameras=len(cameras), frames=len(frames), files=len(outputs)), outputs

        return self.run_guarded(context, export_batch)


CLASSES = (
    CMASK_OT_CreateCompositorNodes,
    CMASK_OT_PreviewColorID,
    CMASK_OT_PreviewSelectedMask,
    CMASK_OT_ExportColorID,
    CMASK_OT_ExportSelectedMask,
    CMASK_OT_ExportAllMasks,
    CMASK_OT_ExportAll,
    CMASK_OT_ExportMultilayerEXR,
    CMASK_OT_ExportCryptomatte,
    CMASK_OT_ExportBatch,
)
