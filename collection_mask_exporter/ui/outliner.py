import bpy


def draw_collection_context(self, context):
    collection = getattr(context, "collection", None)
    if not isinstance(collection, bpy.types.Collection):
        context_id = getattr(context, "id", None)
        collection = context_id if isinstance(context_id, bpy.types.Collection) else None
    if not collection:
        return
    self.layout.separator()
    operator = self.layout.operator(
        "cmask.add_outliner_collection", icon="RENDERLAYERS"
    )
    operator.collection_name = collection.name


def register_outliner_menu():
    menu = getattr(bpy.types, "OUTLINER_MT_collection", None)
    if menu:
        try:
            menu.remove(draw_collection_context)
        except Exception:
            pass
        menu.append(draw_collection_context)


def unregister_outliner_menu():
    menu = getattr(bpy.types, "OUTLINER_MT_collection", None)
    if menu:
        try:
            menu.remove(draw_collection_context)
        except Exception:
            pass
