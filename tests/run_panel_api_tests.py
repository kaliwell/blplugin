# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import ast
import pathlib
import sys
from types import SimpleNamespace

import bpy


panel_path = pathlib.Path(__file__).resolve().parents[1] / "collection_mask_exporter" / "ui" / "panel.py"
root = panel_path.parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
tree = ast.parse(panel_path.read_text(encoding="utf-8"), filename=str(panel_path))
calls = [
    node for node in ast.walk(tree)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and node.func.attr == "prop_search"
]
assert len(calls) == 1
call = calls[0]
assert len(call.args) == 4, "UILayout.prop_search accepts four positional arguments"
assert any(keyword.arg == "text" for keyword in call.keywords), (
    "UILayout.prop_search text must be passed as a keyword"
)
print("CMASK PANEL API TESTS PASSED")

valid_icons = {
    item.identifier
    for item in bpy.types.UILayout.bl_rna.functions["operator"].parameters["icon"].enum_items
}
for path in panel_path.parent.glob("*.py"):
    ui_tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(ui_tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if (keyword.arg == "icon" and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)):
                assert keyword.value.value in valid_icons, (
                    f"Invalid Blender {bpy.app.version_string} icon "
                    f"{keyword.value.value!r} in {path.name}:{node.lineno}"
                )
print("CMASK PANEL ICON TESTS PASSED")


class MockLayout:
    enabled = True
    alert = False

    def box(self):
        return MockLayout()

    def row(self, **_kwargs):
        return MockLayout()

    def label(self, **_kwargs):
        return None

    def separator(self):
        return None

    def prop(self, data, property_name, **_kwargs):
        assert hasattr(data, property_name), property_name

    def prop_search(self, data, property_name, search_data, search_property, *, text):
        assert hasattr(data, property_name), property_name
        assert hasattr(search_data, search_property), search_property
        assert isinstance(text, str)

    def template_list(self, _list_type, _list_id, data, property_name,
                      active_data, active_property, **_kwargs):
        assert hasattr(data, property_name), property_name
        assert hasattr(active_data, active_property), active_property

    def operator(self, operator_id, *, text=None, icon="NONE"):
        namespace, name = operator_id.split(".", 1)
        assert hasattr(getattr(bpy.ops, namespace), name), operator_id
        assert icon in valid_icons, icon
        return SimpleNamespace(direction="")


import collection_mask_exporter as addon
from collection_mask_exporter.ui.panel import CLASSES as PANEL_CLASSES
from collection_mask_exporter.ui.panel import CMASK_PT_MainPanel


assert len(PANEL_CLASSES) == 10
assert PANEL_CLASSES[0] is CMASK_PT_MainPanel
for panel_class in PANEL_CLASSES[1:]:
    assert panel_class.bl_parent_id == CMASK_PT_MainPanel.bl_idname
assert {
    panel_class.bl_label
    for panel_class in PANEL_CLASSES
    if "DEFAULT_CLOSED" not in getattr(panel_class, "bl_options", set())
} == {
    "Collection Mask Exporter",
    "Scan and Groups",
    "Output Settings",
    "One-Click Delivery",
}
print("CMASK COLLAPSIBLE PANEL HIERARCHY TESTS PASSED")

addon.register()
try:
    settings = bpy.context.scene.cmask_settings
    for scan_mode in ("PREFIX", "MANUAL"):
        settings.scan_mode = scan_mode
        settings.dynamic_geometry_enabled = True
        settings.geometry_nodes_split_sources = True
        settings.frame_mode = "RANGE"
        for panel_class in PANEL_CLASSES:
            panel_class.draw(
                SimpleNamespace(
                    layout=MockLayout(),
                    settings=lambda context: context.scene.cmask_settings,
                ),
                bpy.context,
            )
finally:
    addon.unregister()
print("CMASK FULL PANEL DRAW TESTS PASSED")
