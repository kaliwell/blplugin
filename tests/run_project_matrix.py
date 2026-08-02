# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

"""Run the CMask export workflow against an already opened .blend file."""

import importlib
import json
import os
import pathlib
import sys
import time
import traceback

import bpy


def script_args():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 3:
        raise RuntimeError("Expected: <version-label> <output-dir> <expected-blend>")
    return args


VERSION_LABEL, OUTPUT_DIR, EXPECTED_BLEND = script_args()
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_PATH = os.path.join(OUTPUT_DIR, "test_report.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

report = {
    "requested_version": VERSION_LABEL,
    "blender_version": bpy.app.version_string,
    "blend_expected": os.path.abspath(EXPECTED_BLEND),
    "blend_opened": os.path.abspath(bpy.data.filepath) if bpy.data.filepath else "",
    "success": False,
    "groups": [],
    "issues": [],
    "outputs": [],
}


def analyze_flat_id(path):
    image = bpy.data.images.load(path, check_existing=False)
    try:
        pixels = list(image.pixels)
        opaque = [pixels[index:index + 3]
                  for index in range(0, len(pixels), 4)
                  if pixels[index + 3] > 0.99]
        if not opaque:
            raise RuntimeError("彩色 ID 图没有不透明像素")
        bins = {
            tuple(round(channel * 20) / 20 for channel in color)
            for color in opaque
        }
        return len(bins)
    finally:
        bpy.data.images.remove(image)

started = time.perf_counter()
addon = None
try:
    if os.path.normcase(report["blend_opened"]) != os.path.normcase(report["blend_expected"]):
        raise RuntimeError("测试工程未被当前 Blender 正确打开")
    if not bpy.context.scene.camera:
        raise RuntimeError("测试工程没有活动相机")

    addon = importlib.import_module("collection_mask_exporter")
    addon.register()

    scene = bpy.context.scene
    settings = scene.cmask_settings
    settings.scan_mode = "TOP_LEVEL"
    settings.include_children = True
    settings.conflict_mode = "PRIORITY"
    settings.output_directory = OUTPUT_DIR

    # Keep the real camera and composition while limiting matrix-test runtime.
    original_resolution = (
        scene.render.resolution_x,
        scene.render.resolution_y,
        scene.render.resolution_percentage,
    )
    longest = max(scene.render.resolution_x, scene.render.resolution_y)
    scene.render.resolution_percentage = min(100, max(1, int(51200 / longest)))

    bpy.ops.cmask.scan()
    from collection_mask_exporter.core.conflict_checker import validate_groups
    from collection_mask_exporter.core.output_manager import (
        color_id_path, mask_path, multilayer_path,
    )
    from collection_mask_exporter.core.render_pipeline import render_color_id, render_mask

    issues, _resolution = validate_groups(settings)
    report["groups"] = [
        {
            "name": item.collection.name,
            "role": item.role,
            "enabled": item.enabled,
        }
        for item in settings.groups if item.collection
    ]
    report["issues"] = [
        {
            "level": issue.level,
            "code": issue.code,
            "subject": issue.subject,
            "message": issue.message,
        }
        for issue in issues
    ]
    if any(issue.level == "ERROR" for issue in issues):
        raise RuntimeError("场景检查包含错误")

    state_before = {
        obj.name: (tuple(obj.color), obj.hide_render, obj.is_holdout)
        for obj in scene.objects
    }
    engine_before = scene.render.engine

    id_path = color_id_path(scene, settings)
    render_color_id(bpy.context, id_path)
    report["outputs"].append(id_path)
    report["color_id_quantized_bins"] = analyze_flat_id(id_path)
    # Antialiasing creates edge shades; original lit materials create hundreds
    # of additional bins in this fixture. Keep this stable across versions.
    if report["color_id_quantized_bins"] > 200:
        raise RuntimeError(
            "彩色 ID 不是纯色输出，可能被场景合成器或原材质污染"
        )

    targets = [
        item for item in settings.groups
        if item.enabled and item.role == "MASK" and item.collection
    ]
    for mode in ("VISIBLE", "SILHOUETTE"):
        settings.mask_output_mode = mode
        for target in targets:
            path = mask_path(scene, settings, target.collection.name)
            render_mask(bpy.context, target, path)
            report["outputs"].append(path)

    settings.color_depth = "16"
    settings.multilayer_include_color_id = True
    settings.write_report = False
    multilayer_output = multilayer_path(scene, settings)
    if bpy.ops.cmask.export_multilayer_exr() != {"FINISHED"}:
        raise RuntimeError("Multilayer EXR 操作器执行失败")
    report["outputs"].append(multilayer_output)
    import OpenImageIO as oiio
    multilayer_input = oiio.ImageInput.open(multilayer_output)
    if not multilayer_input:
        raise RuntimeError("无法重新读取 Multilayer EXR")
    try:
        multilayer_spec = multilayer_input.spec()
        report["multilayer_channels"] = list(multilayer_spec.channelnames)
        if len(multilayer_spec.channelnames) != (len(targets) + 1) * 4:
            raise RuntimeError("Multilayer EXR 通道数量不正确")
    finally:
        multilayer_input.close()

    missing = [path for path in report["outputs"]
               if not os.path.isfile(path) or os.path.getsize(path) < 100]
    if missing:
        raise RuntimeError("输出文件缺失或为空：" + "、".join(missing))

    state_after = {
        obj.name: (tuple(obj.color), obj.hide_render, obj.is_holdout)
        for obj in scene.objects
    }
    if state_after != state_before or scene.render.engine != engine_before:
        raise RuntimeError("渲染结束后场景状态没有完整恢复")

    report["render_resolution"] = [
        scene.render.resolution_x,
        scene.render.resolution_y,
        scene.render.resolution_percentage,
    ]
    report["source_resolution"] = list(original_resolution)
    report["success"] = True
except Exception as exc:
    report["error"] = str(exc)
    report["traceback"] = traceback.format_exc()
finally:
    report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print("CMASK_MATRIX_RESULT", json.dumps({
        "version": VERSION_LABEL,
        "success": report["success"],
        "error": report.get("error"),
        "outputs": len(report["outputs"]),
        "report": REPORT_PATH,
    }, ensure_ascii=False))
    if addon:
        try:
            addon.unregister()
        except Exception:
            pass

if not report["success"]:
    raise SystemExit(1)
