# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

def is_collection_instance(obj):
    return (
        obj is not None and obj.type == "EMPTY" and
        obj.instance_type == "COLLECTION" and obj.instance_collection is not None
    )


def instance_source_objects(instancer):
    """Return all objects required by a nested Collection Instance graph."""
    if not is_collection_instance(instancer):
        return set()
    return collection_source_objects(instancer.instance_collection)


def collection_source_objects(root_collection):
    """Return recursive object dependencies of a Collection data-block."""
    result = set()
    visited = set()

    def visit_collection(collection):
        if collection in visited:
            return
        visited.add(collection)
        for obj in collection.objects:
            result.add(obj)
            if is_collection_instance(obj):
                visit_collection(obj.instance_collection)
        for child in collection.children:
            visit_collection(child)

    if root_collection is not None:
        visit_collection(root_collection)
    return result
