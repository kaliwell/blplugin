import bpy

from .group_resolver import resolve_groups
from .scanner import ScanIssue, renderable_objects
from ..translations import iface


def validate_groups(settings):
    issues = []
    enabled = [item for item in settings.groups if item.enabled and item.collection]
    if getattr(settings, "dynamic_geometry_enabled", False):
        attribute_name = settings.dynamic_attribute_name.strip()
        if bpy.app.version < (5, 0, 0):
            issues.append(ScanIssue(
                "ERROR", "DYNAMIC_GN_VERSION", "Blender",
                iface("Dynamic GN attributes require Blender 5.0 or newer"),
            ))
        if not attribute_name:
            issues.append(ScanIssue(
                "ERROR", "DYNAMIC_GN_ATTRIBUTE_EMPTY", "Geometry Nodes",
                iface("Dynamic GN attribute name cannot be empty"),
            ))
        dynamic_groups = {}
        for item in enabled:
            dynamic_id = int(getattr(item, "dynamic_id", 0))
            if dynamic_id <= 0:
                continue
            if dynamic_id in dynamic_groups:
                issues.append(ScanIssue(
                    "ERROR", "DYNAMIC_GN_DUPLICATE_ID", str(dynamic_id),
                    iface("Dynamic GN ID {id} is assigned to more than one group").format(
                        id=dynamic_id
                    ),
                ))
            else:
                dynamic_groups[dynamic_id] = item
        if not dynamic_groups:
            issues.append(ScanIssue(
                "ERROR", "DYNAMIC_GN_NO_IDS", "Geometry Nodes",
                iface("Dynamic GN attributes are enabled, but no group has a Dynamic GN ID"),
            ))
    seen_names = set()
    for item in enabled:
        collection = item.collection
        if collection.name in seen_names:
            issues.append(ScanIssue("ERROR", "DUPLICATE_NAME", collection.name,
                                    iface("Duplicate Collection name")))
        seen_names.add(collection.name)
        objects = renderable_objects(collection, settings.include_children)
        if not objects:
            issues.append(ScanIssue("WARNING", "EMPTY", collection.name,
                                    iface("No renderable objects")))

    resolution = resolve_groups(enabled, settings.include_children)
    for obj, groups in resolution.conflicts.items():
        names = ", ".join(item.collection.name for item in groups)
        level = "ERROR" if settings.conflict_mode == "STRICT" else "WARNING"
        issues.append(ScanIssue(level, "MULTIPLE_MEMBERSHIP", obj.name,
                                iface("Belongs to multiple groups: {names}").format(names=names)))
    for instancer, sources in resolution.instance_sources.items():
        owner = resolution.assignments[instancer]
        conflicting = sorted({
            resolution.assignments[source].collection.name
            for source in sources
            if source in resolution.assignments and
            resolution.assignments[source] != owner
        })
        if conflicting:
            level = "ERROR" if settings.conflict_mode == "STRICT" else "WARNING"
            issues.append(ScanIssue(
                level, "INSTANCE_SOURCE_GROUP", instancer.name,
                iface("Instance sources are also managed by other mask groups: {names}").format(
                    names=", ".join(conflicting)
                ),
            ))
    for host, sources in resolution.geometry_node_sources.items():
        owner = resolution.assignments[host]
        source_items = []
        for source in sources:
            item = resolution.assignments.get(source)
            if item is not None and item != owner and item not in source_items:
                source_items.append(item)
        conflicting = sorted({
            item.collection.name for item in source_items
        })
        split_source_mode = (
            getattr(settings, "geometry_nodes_split_sources", False) and
            owner.role == "IGNORE"
        )
        if (getattr(settings, "geometry_nodes_split_sources", False) and
                source_items and owner.role != "IGNORE"):
            issues.append(ScanIssue(
                "ERROR", "GEOMETRY_NODES_SPLIT_HOST_ROLE", host.name,
                iface("Split mode requires host group {name} to use the IGNORE role").format(
                    name=owner.collection.name
                ),
            ))
        elif (getattr(settings, "geometry_nodes_split_sources", False) and
              owner.role == "IGNORE" and
              not any(item.enabled and item.role == "MASK"
                      for item in source_items)):
            issues.append(ScanIssue(
                "WARNING", "GEOMETRY_NODES_SPLIT_NO_MASK", host.name,
                iface("The split host did not resolve any other explicit MASK source group"),
            ))
        if conflicting and not split_source_mode:
            level = "ERROR" if settings.conflict_mode == "STRICT" else "WARNING"
            issues.append(ScanIssue(
                level, "GEOMETRY_NODES_SOURCE_GROUP", host.name,
                iface("Geometry Nodes sources are also managed by other mask groups: {names}").format(
                    names=", ".join(conflicting)
                ),
            ))
    for host, sockets in resolution.geometry_node_unresolved.items():
        issues.append(ScanIssue(
            "WARNING", "GEOMETRY_NODES_DYNAMIC_SOURCE", host.name,
            iface("{count} dynamic instance sources cannot be resolved statically and will be handled as part of the host").format(
                count=len(sockets)
            ),
        ))
    return issues, resolution
