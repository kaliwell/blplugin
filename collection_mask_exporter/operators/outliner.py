import bpy
from bpy.props import StringProperty

from ..core.color_manager import ensure_metadata
from ..core.scanner import walk_collections
from ..translations import iface


class CMASK_OT_AddOutlinerCollection(bpy.types.Operator):
    bl_idname = "cmask.add_outliner_collection"
    bl_label = "Add to CMask (Manual Mode)"
    bl_description = "Keep the current list and add this Collection to manual CMask management"
    bl_options = {"REGISTER", "UNDO"}

    collection_name: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        scene = context.scene
        settings = scene.cmask_settings
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({"ERROR"}, iface("The Collection no longer exists"))
            return {"CANCELLED"}
        if collection not in set(walk_collections(scene.collection)):
            self.report({"ERROR"}, iface("This Collection is not linked to the current scene"))
            return {"CANCELLED"}

        settings.scan_mode = "MANUAL"
        existing = next(
            (index for index, item in enumerate(settings.groups)
             if item.collection == collection),
            None,
        )
        if existing is not None:
            settings.active_group_index = existing
            settings.last_status = iface("{name} is already in the CMask list").format(name=collection.name)
            self.report({"INFO"}, settings.last_status)
            return {"FINISHED"}

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
        collection["cmask_priority"] = index
        settings.active_group_index = index
        settings.last_status = iface("Added from Outliner: {name}").format(name=collection.name)
        self.report({"INFO"}, settings.last_status)
        return {"FINISHED"}


CLASSES = (CMASK_OT_AddOutlinerCollection,)
