# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

import bpy


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import collection_mask_exporter as addon


addon.register()
preferences = bpy.context.preferences.view
original_language = preferences.language
original_interface = preferences.use_translate_interface
try:
    preferences.use_translate_interface = True
    preferences.language = "en_US"
    assert bpy.app.translations.pgettext_iface("Presets") == "Presets"
    assert bpy.app.translations.pgettext_iface("Enable Dynamic GN Attribute") == (
        "Enable Dynamic GN Attribute"
    )

    try:
        preferences.language = "zh_HANS"
    except TypeError:
        preferences.language = "zh_CN"
    assert bpy.app.translations.pgettext_iface("Presets") == "预设"
    assert bpy.app.translations.pgettext_iface("Enable Dynamic GN Attribute") == (
        "启用动态 GN 属性"
    )
    assert bpy.app.translations.pgettext_iface(
        "Dynamic GN attributes require Blender 5.0 or newer"
    ) == "动态 GN 属性需要 Blender 5.0 或更高版本"
finally:
    preferences.language = original_language
    preferences.use_translate_interface = original_interface
    addon.unregister()

print("CMASK TRANSLATION TESTS PASSED")
