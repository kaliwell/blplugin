# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
from datetime import datetime, timezone

import bpy

from .conflict_checker import validate_groups
from .output_manager import blend_stem, ensure_output_dirs, safe_filename


def write_export_report(scene, settings, operation, outputs, elapsed_seconds,
                        success=True, error=None):
    root, _color_dir, _mask_dir = ensure_output_dirs(scene, settings)
    report_dir = os.path.join(root, "Reports")
    os.makedirs(report_dir, exist_ok=True)
    issues, resolution = validate_groups(settings)
    conflicts = []
    for obj, groups in resolution.conflicts.items():
        conflicts.append({
            "object": obj.name,
            "collections": [item.collection.name for item in groups],
            "resolved_to": resolution.assignments[obj].collection.name,
        })
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "blend": bpy.data.filepath,
        "scene": scene.name,
        "camera": scene.camera.name if scene.camera else None,
        "operation": operation,
        "mask_mode": settings.mask_output_mode,
        "output_format": settings.output_format,
        "color_depth": settings.color_depth,
        "edge_adjustment": settings.edge_adjustment,
        "alpha_mode": settings.alpha_mode,
        "transparent_material_mode": settings.transparent_material_mode,
        "create_compositor_nodes": settings.create_compositor_nodes,
        "multilayer_layers": [
            item.name for item in settings.last_multilayer_layers
        ],
        "cryptomatte_depth": int(settings.cryptomatte_depth),
        "geometry_nodes_split_sources": settings.geometry_nodes_split_sources,
        "dynamic_geometry": {
            "enabled": settings.dynamic_geometry_enabled,
            "attribute": settings.dynamic_attribute_name,
            "groups": [
                {
                    "collection": item.collection.name,
                    "id": int(item.dynamic_id),
                }
                for item in settings.groups
                if item.enabled and item.collection and item.dynamic_id > 0
            ],
        },
        "success": success,
        "error": error,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "groups": len([item for item in settings.groups if item.enabled]),
        "outputs": list(outputs),
        "issues": [
            {
                "level": issue.level,
                "code": issue.code,
                "subject": issue.subject,
                "message": issue.message,
            }
            for issue in issues
        ],
        "conflicts": conflicts,
        "geometry_nodes": [
            {
                "host": host.name,
                "resolved_sources": sorted(source.name for source in sources),
                "unresolved_sockets": resolution.geometry_node_unresolved.get(host, []),
            }
            for host, sources in resolution.geometry_node_sources.items()
        ],
    }
    name = safe_filename(f"{blend_stem()}_{operation}_cmask_report") + ".json"
    path = os.path.join(report_dir, name)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path
