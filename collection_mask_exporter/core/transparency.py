from .instances import instance_source_objects, is_collection_instance
from .geometry_nodes import geometry_node_dependencies, is_geometry_nodes_object


def material_uses_transparency(material):
    if material is None:
        return False
    try:
        if material.diffuse_color[3] < 0.999:
            return True
    except (AttributeError, TypeError):
        pass
    if not material.node_tree:
        return False
    for node in material.node_tree.nodes:
        if node.type == "BSDF_TRANSPARENT" and any(
                output.is_linked for output in node.outputs):
            return True
        if node.type == "BSDF_PRINCIPLED":
            alpha = node.inputs.get("Alpha")
            if alpha and (alpha.is_linked or alpha.default_value < 0.999):
                return True
    return False


def object_uses_transparency(obj, _visited=None):
    visited = _visited if _visited is not None else set()
    if obj in visited:
        return False
    visited.add(obj)
    data = getattr(obj, "data", None)
    materials = getattr(data, "materials", ()) if data else ()
    if any(material_uses_transparency(material) for material in materials):
        return True
    if is_collection_instance(obj):
        return any(object_uses_transparency(source, visited)
                   for source in instance_source_objects(obj)
                   if not is_collection_instance(source))
    if is_geometry_nodes_object(obj):
        sources, _unresolved = geometry_node_dependencies(obj)
        return any(object_uses_transparency(source, visited) for source in sources)
    return False
