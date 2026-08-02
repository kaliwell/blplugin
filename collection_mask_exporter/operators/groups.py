import bpy
from bpy.props import EnumProperty

from ..core.color_manager import ensure_metadata
from ..core.scanner import walk_collections
from ..translations import iface


def _write_priorities(settings):
    for index, item in enumerate(settings.groups):
        if item.collection:
            item.collection["cmask_priority"] = index


class CMASK_OT_AddManualGroup(bpy.types.Operator):
    bl_idname = "cmask.add_manual_group"
    bl_label = "Add Collection"

    def execute(self, context):
        settings = context.scene.cmask_settings
        collection = settings.manual_collection
        if not collection:
            self.report({"ERROR"}, iface("Select a Collection first"))
            return {"CANCELLED"}
        scene_collections = set(walk_collections(context.scene.collection))
        if collection not in scene_collections:
            self.report({"ERROR"}, iface("This Collection is not linked to the current scene"))
            return {"CANCELLED"}
        if any(item.collection == collection for item in settings.groups):
            self.report({"WARNING"}, iface("This Collection is already in the list"))
            return {"CANCELLED"}

        index = len(settings.groups)
        color = ensure_metadata(collection, index)
        settings.is_syncing = True
        try:
            item = settings.groups.add()
            item.collection = collection
            item.name = collection.name
            item.enabled = bool(collection.get("cmask_enabled", True))
            item.role = collection.get("cmask_role", "MASK")
            item.color = color
        finally:
            settings.is_syncing = False
        settings.active_group_index = index
        _write_priorities(settings)
        settings.last_status = iface("Added {name}").format(name=collection.name)
        return {"FINISHED"}


class CMASK_OT_RemoveGroup(bpy.types.Operator):
    bl_idname = "cmask.remove_group"
    bl_label = "Remove Selected Group"

    def execute(self, context):
        settings = context.scene.cmask_settings
        index = settings.active_group_index
        if not 0 <= index < len(settings.groups):
            return {"CANCELLED"}
        name = settings.groups[index].collection.name if settings.groups[index].collection else iface("Group")
        settings.groups.remove(index)
        settings.active_group_index = min(index, max(0, len(settings.groups) - 1))
        _write_priorities(settings)
        settings.last_status = iface("Removed {name} from the list").format(name=name)
        return {"FINISHED"}


class CMASK_OT_MoveGroup(bpy.types.Operator):
    bl_idname = "cmask.move_group"
    bl_label = "Change Group Priority"

    direction: EnumProperty(items=(("UP", "Up", "Raise Priority"),
                                  ("DOWN", "Down", "Lower Priority")))

    def execute(self, context):
        settings = context.scene.cmask_settings
        source = settings.active_group_index
        target = source - 1 if self.direction == "UP" else source + 1
        if not (0 <= source < len(settings.groups) and
                0 <= target < len(settings.groups)):
            return {"CANCELLED"}
        settings.groups.move(source, target)
        settings.active_group_index = target
        _write_priorities(settings)
        settings.last_status = iface("Group priority updated")
        return {"FINISHED"}


CLASSES = (CMASK_OT_AddManualGroup, CMASK_OT_RemoveGroup, CMASK_OT_MoveGroup)
