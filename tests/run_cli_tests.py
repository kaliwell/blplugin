# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import pathlib
import sys
import tempfile

import bpy


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import collection_mask_exporter as addon
from collection_mask_exporter.cli import main


addon.register()
scene = bpy.context.scene
scene.render.resolution_x = 48
scene.render.resolution_y = 48
scene.render.resolution_percentage = 100

camera_data = bpy.data.cameras.new("CLI_Camera")
camera = bpy.data.objects.new("CLI_Camera", camera_data)
scene.collection.objects.link(camera)
camera.location = (0.0, 0.0, 7.0)
scene.camera = camera

collection = bpy.data.collections.new("CM_CLI")
scene.collection.children.link(collection)
bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 0.0))
cube = bpy.context.object
for owner in list(cube.users_collection):
    owner.objects.unlink(cube)
collection.objects.link(cube)

with tempfile.TemporaryDirectory(prefix="cmask-cli-test-") as temp:
    job_path = os.path.join(temp, "job.json")
    result_path = os.path.join(temp, "result.json")
    with open(job_path, "w", encoding="utf-8") as handle:
        json.dump({
            "operation": "cryptomatte",
            "scan_mode": "PREFIX",
            "collection_prefix": "CM_",
            "output_directory": temp,
            "cryptomatte_depth": "4",
            "write_report": True,
        }, handle)

    result = main([
        "--job", job_path,
        "--result-json", result_path,
    ], exit_on_error=False)
    assert result["success"] is True
    assert result["operation"] == "cryptomatte"
    assert len(result["outputs"]) == 1
    assert os.path.isfile(result["outputs"][0])
    with open(result_path, "r", encoding="utf-8") as handle:
        stored = json.load(handle)
    assert stored["success"] is True and stored["outputs"] == result["outputs"]

    delivery_root = os.path.join(temp, "delivery")
    delivery = main([
        "--operation", "delivery",
        "--output", delivery_root,
        "--no-report",
    ], exit_on_error=False)
    assert delivery["success"] is True
    assert delivery["operation"] == "delivery"
    assert len(delivery["outputs"]) == 3
    assert all(os.path.isfile(path) for path in delivery["outputs"])
    assert os.path.basename(next(
        path for path in delivery["outputs"]
        if os.path.basename(os.path.dirname(path)) == "Masks"
    )) == "CM_CLI.png"
    photoshop_dir = os.path.join(delivery_root, "Photoshop")
    assert any(name.endswith("_import.jsx") for name in os.listdir(photoshop_dir))

    failed_path = os.path.join(temp, "failed.json")
    failed = main([
        "--operation", "selected-mask",
        "--output", temp,
        "--collection", "MissingCollection",
        "--result-json", failed_path,
    ], exit_on_error=False)
    assert failed["success"] is False
    assert "MissingCollection" in failed["error"]
    with open(failed_path, "r", encoding="utf-8") as handle:
        assert json.load(handle)["success"] is False

    diagnostic = main([
        "--operation", "diagnose",
        "--output", temp,
    ], exit_on_error=False)
    assert diagnostic["success"] is True
    assert diagnostic["operation"] == "diagnose" and not diagnostic["outputs"]
    assert os.path.isfile(diagnostic["diagnostic_report"])

print("CMASK CLI TESTS PASSED")
addon.unregister()
