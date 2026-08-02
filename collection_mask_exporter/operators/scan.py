# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from ..core.scanner import sync_scene_items
from ..translations import iface


class CMASK_OT_Scan(bpy.types.Operator):
    bl_idname = "cmask.scan"
    bl_label = "Scan / Sync"
    bl_description = "Scan Collections with the current rules and synchronize mask groups"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.cmask_settings
        groups = sync_scene_items(context.scene, settings, context.view_layer)
        settings.last_status = iface("Found {count} mask groups").format(count=len(groups))
        settings.issue_count = 0
        settings.issues.clear()
        self.report({"INFO"}, settings.last_status)
        return {"FINISHED"}


CLASSES = (CMASK_OT_Scan,)
