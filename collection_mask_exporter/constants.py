# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

ADDON_VERSION = (0, 7, 0)
SUPPORTED_BLENDER_LINES = {(4, 5), (5, 0), (5, 2)}
SUPPORTED_OBJECT_TYPES = {
    "MESH", "CURVE", "SURFACE", "FONT", "META", "VOLUME", "POINTCLOUD",
}


def is_renderable_object(obj):
    from .core.instances import is_collection_instance
    return (
        obj.type in SUPPORTED_OBJECT_TYPES or
        is_collection_instance(obj)
    )

ROLE_MASK = "MASK"
ROLE_HOLDOUT = "HOLDOUT"
ROLE_OCCLUDER = "OCCLUDER"
ROLE_IGNORE = "IGNORE"

COLLECTION_ROLES = (
    (ROLE_MASK, "Mask", "Export an independent mask and include it in the color ID"),
    (ROLE_HOLDOUT, "Holdout", "Cut a transparent area from the result"),
    (ROLE_OCCLUDER, "Occluder", "Preserve occlusion without exporting a separate mask"),
    (ROLE_IGNORE, "Ignore", "Exclude completely from CMask processing"),
)

PALETTE = (
    (1.0, 0.05, 0.05, 1.0),
    (0.05, 1.0, 0.10, 1.0),
    (0.05, 0.20, 1.0, 1.0),
    (1.0, 0.85, 0.05, 1.0),
    (1.0, 0.05, 0.80, 1.0),
    (0.05, 0.90, 1.0, 1.0),
    (1.0, 0.35, 0.05, 1.0),
    (0.55, 0.10, 1.0, 1.0),
    (0.45, 1.0, 0.05, 1.0),
    (0.05, 0.55, 1.0, 1.0),
    (1.0, 0.35, 0.60, 1.0),
    (0.90, 0.75, 0.20, 1.0),
)
