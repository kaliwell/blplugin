from collections import defaultdict
from dataclasses import dataclass

from ..constants import is_renderable_object
from .instances import instance_source_objects, is_collection_instance
from .geometry_nodes import geometry_node_dependencies, is_geometry_nodes_object


@dataclass
class Resolution:
    assignments: dict
    memberships: dict
    conflicts: dict
    instance_sources: dict
    geometry_node_sources: dict
    geometry_node_unresolved: dict


def _descendants(collection):
    for child in collection.children:
        yield child
        yield from _descendants(child)


def _inherited_objects(collection, explicit):
    """Collect descendants without crossing an explicit group boundary."""
    objects = set(collection.objects)
    for child in collection.children:
        if child in explicit:
            continue
        objects.update(_inherited_objects(child, explicit))
    return objects


def resolve_groups(group_items, include_children=True, include_disabled=False):
    """Resolve each object to the highest-priority enabled group.

    Explicit nested groups take ownership before their ancestors. Remaining
    multi-link conflicts are resolved by UI order (lower index wins).
    """
    enabled = [
        item for item in group_items
        if item.collection and (include_disabled or item.enabled)
    ]
    explicit = {item.collection for item in enabled}
    memberships = defaultdict(list)

    for priority, item in enumerate(enabled):
        collection = item.collection
        objects = (_inherited_objects(collection, explicit)
                   if include_children else set(collection.objects))
        for obj in objects:
            if is_renderable_object(obj):
                memberships[obj].append((priority, item))

    assignments = {}
    conflicts = {}
    for obj, choices in memberships.items():
        choices.sort(key=lambda entry: entry[0])
        assignments[obj] = choices[0][1]
        unique = []
        for _, item in choices:
            if item not in unique:
                unique.append(item)
        if len(unique) > 1:
            conflicts[obj] = unique
    instance_sources = {
        obj: instance_source_objects(obj)
        for obj in assignments if is_collection_instance(obj)
    }
    geometry_node_sources = {}
    geometry_node_unresolved = {}
    for obj in assignments:
        if not is_geometry_nodes_object(obj):
            continue
        sources, unresolved = geometry_node_dependencies(obj)
        geometry_node_sources[obj] = sources
        if unresolved:
            geometry_node_unresolved[obj] = unresolved
    return Resolution(
        assignments, dict(memberships), conflicts, instance_sources,
        geometry_node_sources, geometry_node_unresolved,
    )
