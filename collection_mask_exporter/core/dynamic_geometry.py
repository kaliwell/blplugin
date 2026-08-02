from dataclasses import dataclass, field
import uuid

import bmesh
import bpy

from ..translations import iface


TEMP_COLLECTION_PREFIX = "__CMASK_DYNAMIC"


@dataclass
class DynamicGeometryResources:
    collection: object = None
    objects: list = field(default_factory=list)
    meshes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _dynamic_group_map(settings):
    result = {}
    for item in settings.groups:
        dynamic_id = int(getattr(item, "dynamic_id", 0))
        if not item.enabled or not item.collection or dynamic_id <= 0:
            continue
        if dynamic_id in result:
            raise RuntimeError(iface(
                "Dynamic GN ID {id} is assigned to more than one group"
            ).format(id=dynamic_id))
        result[dynamic_id] = item
    if not result:
        raise RuntimeError(iface(
            "Dynamic GN attributes are enabled, but no group has a Dynamic GN ID"
        ))
    return result


def _partition_face_mesh(source_mesh, attribute_name, dynamic_id, name):
    mesh = source_mesh.copy()
    mesh.name = name
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        layer = bm.faces.layers.int.get(attribute_name)
        if layer is None:
            bpy.data.meshes.remove(mesh)
            return None
        remove = [face for face in bm.faces if int(face[layer]) != dynamic_id]
        if remove:
            bmesh.ops.delete(bm, geom=remove, context="FACES")
        if not bm.faces:
            bpy.data.meshes.remove(mesh)
            return None
        bm.to_mesh(mesh)
        mesh.update()
        return mesh
    finally:
        bm.free()


def prepare_dynamic_geometry(context, resolution, settings):
    resources = DynamicGeometryResources()
    if not getattr(settings, "dynamic_geometry_enabled", False):
        return resources
    if bpy.app.version < (5, 0, 0) or not hasattr(bpy.types.Object, "evaluated_geometry"):
        raise RuntimeError(iface("Dynamic GN attributes require Blender 5.0 or newer"))

    attribute_name = settings.dynamic_attribute_name.strip()
    if not attribute_name:
        raise RuntimeError(iface("Dynamic GN attribute name cannot be empty"))
    groups = _dynamic_group_map(settings)
    depsgraph = context.evaluated_depsgraph_get()
    prepared = 0

    for host, owner in list(resolution.assignments.items()):
        if owner.role != "IGNORE" or not any(
                modifier.type == "NODES" for modifier in host.modifiers):
            continue
        evaluated = host.evaluated_get(depsgraph)
        source_mesh = bpy.data.meshes.new_from_object(
            evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
        )
        if source_mesh is None:
            continue
        try:
            attribute = source_mesh.attributes.get(attribute_name)
            if (attribute is None or attribute.domain != "FACE" or
                    attribute.data_type != "INT"):
                continue
            values = {int(item.value) for item in attribute.data}
            unknown = sorted(value for value in values if value > 0 and value not in groups)
            if unknown:
                resources.warnings.append(
                    f"{host.name}: unmapped {attribute_name} values {unknown}"
                )
            if resources.collection is None:
                resources.collection = bpy.data.collections.new(
                    f"{TEMP_COLLECTION_PREFIX}_{uuid.uuid4().hex}"
                )
                context.scene.collection.children.link(resources.collection)
            for dynamic_id, item in groups.items():
                if dynamic_id not in values:
                    continue
                mesh = _partition_face_mesh(
                    source_mesh, attribute_name, dynamic_id,
                    f"{TEMP_COLLECTION_PREFIX}_{host.name}_{dynamic_id}",
                )
                if mesh is None:
                    continue
                obj = bpy.data.objects.new(mesh.name, mesh)
                obj.matrix_world = host.matrix_world
                obj["cmask_dynamic_host"] = host.name
                obj["cmask_dynamic_id"] = dynamic_id
                resources.collection.objects.link(obj)
                resources.meshes.append(mesh)
                resources.objects.append(obj)
                resolution.assignments[obj] = item
                prepared += 1
        finally:
            bpy.data.meshes.remove(source_mesh)

    if not prepared:
        cleanup_dynamic_geometry(resources)
        raise RuntimeError(iface(
            "No evaluated IGNORE Geometry Nodes host contains a FACE/INT '{attribute}' attribute"
        ).format(attribute=attribute_name))
    return resources


def cleanup_dynamic_geometry(resources):
    errors = []
    if resources is None:
        return errors
    for obj in reversed(resources.objects):
        try:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        except Exception as exc:
            errors.append(f"dynamic object {getattr(obj, 'name', '?')}: {exc}")
    for mesh in reversed(resources.meshes):
        try:
            if mesh.name in bpy.data.meshes:
                bpy.data.meshes.remove(mesh)
        except Exception as exc:
            errors.append(f"dynamic mesh {getattr(mesh, 'name', '?')}: {exc}")
    collection = resources.collection
    try:
        if collection and collection.name in bpy.data.collections:
            bpy.data.collections.remove(collection)
    except Exception as exc:
        errors.append(f"dynamic collection: {exc}")
    return errors
