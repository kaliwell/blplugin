# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import pathlib
import sys
import tempfile

import bpy


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

addon = importlib.import_module("collection_mask_exporter")
registered_here = False
if not hasattr(bpy.types.Scene, "cmask_settings"):
    addon.register()
    registered_here = True

scene = bpy.context.scene
assert scene.name == "CMask Demo"
settings = scene.cmask_settings
assert len(settings.presets) == 1
assert settings.presets[0].name == "演示交付"
assert len(settings.groups) == 4
roles = {item.collection.name: item.role for item in settings.groups}
assert roles == {
    "CM_Body": "MASK",
    "CM_Detail": "MASK",
    "CM_Occluder": "OCCLUDER",
    "CM_Holdout": "HOLDOUT",
}
assert bpy.ops.cmask.validate() == {"FINISHED"}
assert not any(issue.level == "ERROR" for issue in settings.issues)

output = pathlib.Path(tempfile.mkdtemp(prefix="cmask-sample-test-"))
settings.output_directory = str(output)
settings.output_format = "PNG"
settings.color_depth = "8"
settings.write_report = True
assert bpy.ops.cmask.export_delivery() == {"FINISHED"}
paths = [pathlib.Path(item.path) for item in settings.last_outputs]
assert len(paths) == 4 and all(path.is_file() for path in paths)
assert {path.parent.name for path in paths} == {"Render", "Color_ID", "Masks"}
assert {path.stem for path in paths if path.parent.name == "Masks"} == {
    "CM_Body", "CM_Detail",
}
assert len(list((output / "Reports").glob("*.json"))) == 1

handoff = output / "Photoshop"
assert len(list(handoff.glob("*.jsx"))) == 1
assert len(list(handoff.glob("*_handoff.json"))) == 1
with open(next(handoff.glob("*_handoff.json")), "r", encoding="utf-8") as handle:
    manifest = __import__("json").load(handle)
mask_layers = {
    item["layer"] for item in manifest["outputs"]
    if pathlib.Path(item["path"]).parent.name == "Masks"
}
assert mask_layers == {"CM_Body", "CM_Detail"}

print("CMASK SAMPLE PROJECT TESTS PASSED")
if registered_here:
    addon.unregister()
