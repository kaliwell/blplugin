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
    assert bpy.app.translations.pgettext_iface(
        "One-Click Render + Masks + Photoshop"
    ) == "一键导出渲染 + 蒙版 + Photoshop"
    assert bpy.app.translations.pgettext_iface(
        "Use Color ID Color for Masks"
    ) == "蒙版使用 Color ID 颜色"
    operator_context = bpy.app.translations.contexts.operator_default
    assert bpy.app.translations.pgettext(
        "Check Scene", operator_context
    ) == "检查场景"
    assert bpy.app.translations.pgettext(
        "One-Click Render + Masks + Photoshop", operator_context
    ) == "一键导出渲染 + 蒙版 + Photoshop"
    assert bpy.app.translations.pgettext_iface(
        "Collection Mask Exporter"
    ) == "集合蒙版导出器"
    assert bpy.app.translations.pgettext_iface(
        "Alpha Storage"
    ) == "透明度存储方式"
    expected_panel_titles = {
        "Scan and Groups": "扫描与组",
        "Validation": "检查与诊断",
        "Geometry Nodes Settings": "Geometry Nodes 设置",
        "One-Click Delivery": "一键交付",
        "Individual Exports": "单项导出",
        "Advanced Output": "高级输出",
    }
    for source, translated in expected_panel_titles.items():
        assert bpy.app.translations.pgettext_iface(source) == translated
finally:
    preferences.language = original_language
    preferences.use_translate_interface = original_interface
    addon.unregister()

print("CMASK TRANSLATION TESTS PASSED")
