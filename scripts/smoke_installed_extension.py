# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib

import bpy


addon = importlib.import_module(
    "bl_ext.user_default.collection_mask_exporter"
)
constants = importlib.import_module(
    "bl_ext.user_default.collection_mask_exporter.constants"
)

assert constants.ADDON_VERSION == (0, 9, 1)
assert hasattr(bpy.types.Scene, "cmask_settings")
assert hasattr(bpy.ops.cmask, "scan")
assert hasattr(bpy.ops.cmask, "compatibility_report")
assert bpy.context.scene.cmask_settings is not None
assert addon is not None

print("CMASK INSTALLED ZIP SMOKE TEST PASSED", bpy.app.version_string)
