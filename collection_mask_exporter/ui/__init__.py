from .panel import CLASSES as PANEL_CLASSES
from .ui_list import CLASSES as LIST_CLASSES
from .outliner import register_outliner_menu, unregister_outliner_menu

CLASSES = (*LIST_CLASSES, *PANEL_CLASSES)
