# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy


class CMASK_UL_Groups(bpy.types.UIList):
    def draw_item(self, context, layout, _data, item, _icon, _active_data,
                  _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.label(text=item.collection.name if item.collection else "<Invalid Collection>",
                  icon="OUTLINER_COLLECTION")
        row.prop(item, "color", text="")
        row.prop(item, "role", text="")
        if context.scene.cmask_settings.dynamic_geometry_enabled:
            row.prop(item, "dynamic_id", text="ID")


CLASSES = (CMASK_UL_Groups,)
