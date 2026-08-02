# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

def iter_layer_collections(root):
    yield root
    for child in root.children:
        yield from iter_layer_collections(child)


def collection_layer_map(view_layer):
    return {
        layer.collection: layer
        for layer in iter_layer_collections(view_layer.layer_collection)
    }


def reset_layer_flags(view_layer):
    for layer in iter_layer_collections(view_layer.layer_collection):
        layer.exclude = False
        layer.holdout = False
        layer.indirect_only = False


def configure_group_layers(view_layer, group_items, target=None, mode="VISIBLE",
                           color_id=False, reset=True):
    mapping = collection_layer_map(view_layer)
    if reset:
        reset_layer_flags(view_layer)
    for item in group_items:
        if not item.collection or item.collection not in mapping:
            continue
        layer = mapping[item.collection]
        if not item.enabled or item.role == "IGNORE":
            layer.exclude = True
        elif color_id:
            layer.holdout = item.role in {"HOLDOUT", "OCCLUDER"}
        elif item == target:
            layer.exclude = False
            layer.holdout = False
        elif mode == "VISIBLE":
            layer.holdout = True
        else:
            layer.exclude = True
