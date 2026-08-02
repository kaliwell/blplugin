# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

from .operators import CLASSES as OPERATOR_CLASSES
from .properties import register_properties, unregister_properties
from .ui import CLASSES as UI_CLASSES
from .ui import register_outliner_menu, unregister_outliner_menu
from .translations import register_translations, unregister_translations


CLASSES = (*OPERATOR_CLASSES, *UI_CLASSES)


def register():
    import bpy
    register_translations()
    register_properties()
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    register_outliner_menu()


def unregister():
    import bpy
    unregister_outliner_menu()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    unregister_properties()
    unregister_translations()
