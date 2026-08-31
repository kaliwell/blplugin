# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

"""Background/ render-farm entry point for Collection Mask Exporter."""

import argparse
import json
import os
import sys
import time

import bpy

from .constants import ADDON_VERSION
from .registration import register


OPERATIONS = {
    "color-id": "cmask.export_color_id",
    "selected-mask": "cmask.export_selected_mask",
    "all-masks": "cmask.export_all_masks",
    "selected-cutout": "cmask.export_selected_cutout",
    "all-cutouts": "cmask.export_all_cutouts",
    "all": "cmask.export_all",
    "delivery": "cmask.export_delivery",
    "multilayer": "cmask.export_multilayer_exr",
    "cryptomatte": "cmask.export_cryptomatte",
    "batch": "cmask.export_batch",
    "diagnose": "cmask.compatibility_report",
}

SETTING_FIELDS = {
    "scan_mode", "collection_prefix", "scan_visible_only", "include_children",
    "conflict_mode", "mask_output_mode", "output_directory", "output_format",
    "color_depth", "edge_adjustment", "alpha_mode", "transparent_material_mode",
    "mask_use_group_name", "mask_use_group_color", "mask_edge_protection",
    "filename_template", "write_report", "create_compositor_nodes",
    "multilayer_include_color_id", "cryptomatte_depth", "camera_mode",
    "geometry_nodes_split_sources", "dynamic_geometry_enabled",
    "dynamic_attribute_name", "delivery_include_cutouts",
    "frame_mode", "frame_start", "frame_end", "frame_step",
}
JOB_FIELDS = SETTING_FIELDS | {
    "scene", "preset", "operation", "collection", "result_json",
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="CMask CLI",
        description="Run Collection Mask Exporter in Blender background mode.",
    )
    parser.add_argument("--job", help="JSON task file; explicit CLI options override it")
    parser.add_argument("--scene")
    parser.add_argument("--preset")
    parser.add_argument("--operation", choices=tuple(OPERATIONS))
    parser.add_argument("--output", dest="output_directory")
    parser.add_argument("--scan-mode", choices=("PREFIX", "TOP_LEVEL", "MANUAL"))
    parser.add_argument("--prefix", dest="collection_prefix")
    parser.add_argument("--visible-only", dest="scan_visible_only",
                        action="store_true", default=None)
    parser.add_argument(
        "--collection", help="Collection for selected-mask or selected-cutout"
    )
    parser.add_argument("--format", dest="output_format", choices=("PNG", "OPEN_EXR"))
    parser.add_argument("--depth", dest="color_depth", choices=("8", "16", "32"))
    parser.add_argument("--cryptomatte-depth", choices=("2", "4", "6", "8", "10", "12"))
    parser.add_argument("--mask-mode", dest="mask_output_mode",
                        choices=("VISIBLE", "SILHOUETTE"))
    parser.add_argument("--all-cameras", action="store_true", default=None)
    parser.add_argument("--frame-range", nargs=3, type=int,
                        metavar=("START", "END", "STEP"))
    parser.add_argument("--no-report", action="store_true", default=None)
    parser.add_argument("--result-json", help="Write a machine-readable execution result")
    return parser


def _blender_arguments():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _load_job(path):
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        job = json.load(handle)
    if not isinstance(job, dict):
        raise ValueError("CMask JSON 任务必须是一个对象")
    unknown = sorted(set(job) - JOB_FIELDS)
    if unknown:
        raise ValueError("CMask JSON 任务包含未知字段：" + ", ".join(unknown))
    return job


def resolve_config(arguments):
    args = build_parser().parse_args(arguments)
    config = _load_job(args.job)
    for field in (
        "scene", "preset", "operation", "output_directory", "scan_mode",
        "collection_prefix", "scan_visible_only", "collection", "output_format",
        "color_depth", "cryptomatte_depth", "mask_output_mode", "result_json",
    ):
        value = getattr(args, field)
        if value is not None:
            config[field] = value
    if args.all_cameras:
        config["camera_mode"] = "ALL"
    if args.frame_range is not None:
        start, end, step = args.frame_range
        config.update(frame_mode="RANGE", frame_start=start,
                      frame_end=end, frame_step=step)
    if args.no_report:
        config["write_report"] = False
    config.setdefault("operation", "all")
    return config


def _activate_scene(name):
    if not name:
        return bpy.context.scene
    scene = bpy.data.scenes.get(name)
    if scene is None:
        raise ValueError(f"找不到场景：{name}")
    if bpy.context.window:
        bpy.context.window.scene = scene
    elif bpy.context.scene != scene:
        raise RuntimeError("后台上下文无法切换到指定场景")
    return scene


def _apply_config(scene, config):
    settings = scene.cmask_settings
    preset = config.get("preset")
    if preset:
        settings.preset_name = preset
        if bpy.ops.cmask.apply_preset() != {"FINISHED"}:
            raise RuntimeError(settings.last_status or f"无法应用预设：{preset}")
    for field in SETTING_FIELDS:
        if field in config:
            setattr(settings, field, config[field])
    if bpy.ops.cmask.scan() != {"FINISHED"}:
        raise RuntimeError(settings.last_status or "Collection 扫描失败")
    selected = config.get("collection")
    if selected:
        index = next(
            (index for index, item in enumerate(settings.groups)
             if item.collection and item.collection.name == selected), None
        )
        if index is None:
            raise ValueError(f"扫描结果中找不到 Collection：{selected}")
        settings.active_group_index = index
    return settings


def _run_operator(operation):
    path = OPERATIONS.get(operation)
    if path is None:
        raise ValueError(f"未知导出操作：{operation}")
    namespace, operator = path.split(".", 1)
    result = getattr(getattr(bpy.ops, namespace), operator)()
    if result != {"FINISHED"}:
        raise RuntimeError(f"CMask 操作失败：{operation}")


def _write_result(path, payload):
    if not path:
        return
    absolute = os.path.abspath(bpy.path.abspath(path))
    directory = os.path.dirname(absolute)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(absolute, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def run(arguments=None):
    started = time.perf_counter()
    config = resolve_config(_blender_arguments() if arguments is None else arguments)
    if not hasattr(bpy.types.Scene, "cmask_settings"):
        register()
    scene = _activate_scene(config.get("scene"))
    operation = config["operation"]
    settings = _apply_config(scene, config)
    _run_operator(operation)
    return {
        "success": True,
        "version": ".".join(str(value) for value in ADDON_VERSION),
        "blender_version": bpy.app.version_string,
        "blend": bpy.data.filepath,
        "scene": scene.name,
        "operation": operation,
        "status": settings.last_status,
        "outputs": ([] if operation == "diagnose" else
                    [item.path for item in settings.last_outputs]),
        "diagnostic_report": settings.last_diagnostic_report or None,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "result_json": config.get("result_json"),
    }


def main(arguments=None, exit_on_error=True):
    result_path = None
    try:
        config = resolve_config(_blender_arguments() if arguments is None else arguments)
        result_path = config.get("result_json")
        payload = run(_blender_arguments() if arguments is None else arguments)
        _write_result(result_path, payload)
        print("CMASK_CLI_RESULT=" + json.dumps(payload, ensure_ascii=False))
        return payload
    except Exception as exc:
        payload = {
            "success": False,
            "version": ".".join(str(value) for value in ADDON_VERSION),
            "error": str(exc),
        }
        try:
            _write_result(result_path, payload)
        except Exception as write_exc:
            payload["result_write_error"] = str(write_exc)
        print("CMASK_CLI_RESULT=" + json.dumps(payload, ensure_ascii=False))
        if exit_on_error:
            raise SystemExit(2) from exc
        return payload


if __name__ == "__main__":
    main()
