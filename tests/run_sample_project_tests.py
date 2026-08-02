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
assert bpy.ops.cmask.export_all() == {"FINISHED"}
paths = [pathlib.Path(item.path) for item in settings.last_outputs]
assert len(paths) == 3 and all(path.is_file() for path in paths)
assert len(list((output / "Reports").glob("*.json"))) == 1

assert bpy.ops.cmask.create_photoshop_handoff() == {"FINISHED"}
handoff = output / "Photoshop"
assert len(list(handoff.glob("*.jsx"))) == 1
assert len(list(handoff.glob("*_handoff.json"))) == 1

print("CMASK SAMPLE PROJECT TESTS PASSED")
if registered_here:
    addon.unregister()
