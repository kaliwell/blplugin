# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.props import BoolProperty, StringProperty

from ..core.isolation import (
    clear_render_isolation, isolate_collection, isolate_object,
)
from ..translations import iface


def _start_render_if_requested(operator, context, render_now):
    if not render_now:
        return {"FINISHED"}
    if not context.scene.camera:
        operator.report({"WARNING"}, iface(
            "Solo render is active, but the scene has no active camera"
        ))
        return {"FINISHED"}
    context.view_layer.update()
    if bpy.app.background:
        result = bpy.ops.render.render(
            "EXEC_DEFAULT", write_still=False, scene=context.scene.name
        )
    else:
        result = bpy.ops.render.render("INVOKE_DEFAULT", scene=context.scene.name)
    if "CANCELLED" in result:
        operator.report({"WARNING"}, iface(
            "Solo render is active, but Blender could not start rendering"
        ))
    return {"FINISHED"}


class CMASK_OT_IsolateCollectionRender(bpy.types.Operator):
    bl_idname = "cmask.isolate_collection_render"
    bl_label = "Solo Render Collection"
    bl_description = "Render this Collection normally while all other visible objects remain transparent occluders"
    bl_options = {"REGISTER"}

    collection_name: StringProperty(options={"HIDDEN"})
    render_now: BoolProperty(default=True, options={"HIDDEN"})

    def execute(self, context):
        settings = context.scene.cmask_settings
        collection = bpy.data.collections.get(self.collection_name)
        if collection is None:
            index = settings.active_group_index
            if 0 <= index < len(settings.groups):
                collection = settings.groups[index].collection
        try:
            count = isolate_collection(
                context.scene, context.view_layer, collection
            )
        except (RuntimeError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        settings.last_status = iface(
            "Solo render active for {name} ({count} objects); other objects are transparent occluders"
        ).format(name=collection.name, count=count)
        self.report({"INFO"}, settings.last_status)
        return _start_render_if_requested(self, context, self.render_now)


class CMASK_OT_IsolateObjectRender(bpy.types.Operator):
    bl_idname = "cmask.isolate_object_render"
    bl_label = "Solo Render Object"
    bl_description = "Render this object normally while all other visible objects remain transparent occluders"
    bl_options = {"REGISTER"}

    object_name: StringProperty(options={"HIDDEN"})
    render_now: BoolProperty(default=True, options={"HIDDEN"})

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name) or context.active_object
        try:
            count = isolate_object(context.scene, context.view_layer, obj)
        except (RuntimeError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        settings = context.scene.cmask_settings
        settings.last_status = iface(
            "Solo render active for {name}; other objects are transparent occluders"
        ).format(name=obj.name)
        self.report({"INFO"}, settings.last_status)
        return _start_render_if_requested(self, context, self.render_now)


class CMASK_OT_ClearIsolateRender(bpy.types.Operator):
    bl_idname = "cmask.clear_isolate_render"
    bl_label = "Cancel Solo Render"
    bl_description = "Restore all render visibility, Holdout, View Layer, and transparent-film settings"
    bl_options = {"REGISTER"}

    def execute(self, context):
        errors = clear_render_isolation(context.scene)
        settings = context.scene.cmask_settings
        if errors:
            settings.last_status = iface(
                "Solo render cancelled with restore warnings: {errors}"
            ).format(errors="; ".join(errors))
            self.report({"WARNING"}, settings.last_status)
        else:
            settings.last_status = iface("Solo render cancelled; scene state restored")
            self.report({"INFO"}, settings.last_status)
        return {"FINISHED"}


CLASSES = (
    CMASK_OT_IsolateCollectionRender,
    CMASK_OT_IsolateObjectRender,
    CMASK_OT_ClearIsolateRender,
)
