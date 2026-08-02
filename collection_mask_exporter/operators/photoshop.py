# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from ..core.photoshop import PhotoshopHandoffError, write_photoshop_handoff
from ..translations import iface


class CMASK_OT_CreatePhotoshopHandoff(bpy.types.Operator):
    bl_idname = "cmask.create_photoshop_handoff"
    bl_label = "Create Photoshop Import Script"
    bl_description = "Create a JSX from recent outputs to build layers and save a PSD"

    def execute(self, context):
        settings = context.scene.cmask_settings
        try:
            jsx_path, manifest_path, psd_path = write_photoshop_handoff(
                context.scene, settings
            )
        except (OSError, PhotoshopHandoffError, ValueError) as exc:
            settings.last_status = iface("Failed: {error}").format(error=exc)
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        message = iface("Photoshop script created: {jsx}; target PSD: {psd}").format(
            jsx=jsx_path, psd=psd_path
        )
        settings.last_status = message
        self.report({"INFO"}, message)
        return {"FINISHED"}


CLASSES = (CMASK_OT_CreatePhotoshopHandoff,)
