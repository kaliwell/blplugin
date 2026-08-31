# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from ..constants import is_renderable_object


def draw_collection_context(self, context):
    collection = getattr(context, "collection", None)
    if not isinstance(collection, bpy.types.Collection):
        context_id = getattr(context, "id", None)
        collection = context_id if isinstance(context_id, bpy.types.Collection) else None
    if not collection:
        return
    self.layout.separator()
    operator = self.layout.operator(
        "cmask.add_outliner_collection", icon="RENDERLAYERS"
    )
    operator.collection_name = collection.name
    operator = self.layout.operator(
        "cmask.isolate_collection_render", icon="RESTRICT_RENDER_OFF"
    )
    operator.collection_name = collection.name
    if context.scene.cmask_settings.isolate_active:
        self.layout.operator("cmask.clear_isolate_render", icon="LOOP_BACK")


def draw_object_context(self, context):
    context_id = getattr(context, "id", None)
    obj = context_id if isinstance(context_id, bpy.types.Object) else None
    if obj is None:
        obj = getattr(context, "active_object", None)
    if obj is None:
        return
    settings = context.scene.cmask_settings
    renderable = is_renderable_object(obj)
    if not renderable and not settings.isolate_active:
        return
    self.layout.separator()
    if renderable:
        operator = self.layout.operator(
            "cmask.isolate_object_render", icon="RESTRICT_RENDER_OFF"
        )
        operator.object_name = obj.name
    if settings.isolate_active:
        self.layout.operator("cmask.clear_isolate_render", icon="LOOP_BACK")


def _menus():
    return (
        (getattr(bpy.types, "OUTLINER_MT_collection", None), draw_collection_context),
        (getattr(bpy.types, "OUTLINER_MT_object", None), draw_object_context),
        (getattr(bpy.types, "VIEW3D_MT_object_context_menu", None), draw_object_context),
    )


def register_outliner_menu():
    for menu, callback in _menus():
        if not menu:
            continue
        try:
            menu.remove(callback)
        except Exception:
            pass
        menu.append(callback)


def unregister_outliner_menu():
    for menu, callback in _menus():
        if not menu:
            continue
        try:
            menu.remove(callback)
        except Exception:
            pass
