import json
import os
import platform
import sys
from datetime import datetime, timezone

import bpy

from ..constants import ADDON_VERSION, SUPPORTED_BLENDER_LINES
from .output_manager import blend_stem, ensure_output_dirs, safe_filename


def _check(checks, key, required, callback, description):
    try:
        passed, detail = callback()
    except Exception as exc:
        passed, detail = False, f"{type(exc).__name__}: {exc}"
    checks.append({
        "key": key,
        "required": bool(required),
        "passed": bool(passed),
        "description": description,
        "detail": str(detail),
    })


def _rna_has(rna_type, *names):
    available = set(rna_type.bl_rna.properties.keys())
    return all(name in available for name in names)


def blender_support_status(version):
    version = tuple(version[:3])
    if version < (4, 5, 0):
        support_status = "UNSUPPORTED"
    elif version >= (6, 0, 0):
        support_status = "FUTURE_UNVALIDATED"
    elif version[:2] not in SUPPORTED_BLENDER_LINES:
        support_status = "UNVALIDATED"
    else:
        support_status = "SUPPORTED"
    return support_status


def collect_compatibility(scene=None):
    scene = scene or bpy.context.scene
    version = tuple(bpy.app.version[:3])
    support_status = blender_support_status(version)

    checks = []
    _check(checks, "view_layer_create_remove", True, lambda: (
        hasattr(scene.view_layers, "new") and hasattr(scene.view_layers, "remove"),
        "Scene.view_layers new/remove",
    ), "临时 View Layer 创建与删除")
    _check(checks, "view_layer_material_override", True, lambda: (
        _rna_has(bpy.types.ViewLayer, "material_override"),
        "ViewLayer.material_override",
    ), "非破坏性材质覆盖")
    _check(checks, "layer_collection_flags", True, lambda: (
        _rna_has(bpy.types.LayerCollection, "exclude", "holdout", "indirect_only"),
        "LayerCollection exclude/holdout/indirect_only",
    ), "Collection 可见性和遮挡控制")
    _check(checks, "material_node_tree", True, lambda: (
        _rna_has(bpy.types.Material, "node_tree"),
        "Material.node_tree available",
    ), "临时 Emission 材质节点")
    _check(checks, "render_image_settings", True, lambda: (
        all(hasattr(scene.render.image_settings, name)
            for name in ("file_format", "color_mode", "color_depth")),
        "ImageFormatSettings format/mode/depth",
    ), "PNG/OpenEXR 格式和位深")
    _check(checks, "compositor_api", False, lambda: (
        (hasattr(scene, "compositing_node_group") if version >= (5, 0, 0)
         else hasattr(scene, "node_tree")),
        ("Scene.compositing_node_group" if version >= (5, 0, 0)
         else "Scene.node_tree"),
    ), "导出后创建 Compositor 图像节点")

    def openimageio():
        import OpenImageIO as oiio
        detail = getattr(oiio, "VERSION_STRING", None)
        if detail is None:
            detail = getattr(oiio, "__version__", "available")
        return True, detail

    _check(checks, "openimageio", False, openimageio,
           "Multilayer EXR 与 Collection Cryptomatte")

    required_failures = [
        item["key"] for item in checks if item["required"] and not item["passed"]
    ]
    optional_failures = [
        item["key"] for item in checks if not item["required"] and not item["passed"]
    ]
    return {
        "schema": "cmask.compatibility.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "addon_version": ".".join(str(value) for value in ADDON_VERSION),
        "blender_version": bpy.app.version_string,
        "blender_version_tuple": list(version),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "background": bool(bpy.app.background),
        "support_status": support_status,
        "compatible": not required_failures,
        "required_failures": required_failures,
        "optional_failures": optional_failures,
        "checks": checks,
        "notes": (
            ["Blender 6.0+ 尚未纳入正式发布版验证矩阵"]
            if support_status == "FUTURE_UNVALIDATED" else
            ["当前仅正式支持 Blender 4.5.x、5.0.x 和 5.2.x"]
            if support_status == "UNVALIDATED" else []
        ),
    }


def write_compatibility_report(scene, settings):
    root, _color_dir, _mask_dir = ensure_output_dirs(scene, settings)
    report_dir = os.path.join(root, "Reports")
    os.makedirs(report_dir, exist_ok=True)
    path = os.path.join(
        report_dir,
        safe_filename(f"{blend_stem()}_compatibility_report") + ".json",
    )
    payload = collect_compatibility(scene)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path, payload
