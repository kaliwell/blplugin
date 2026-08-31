# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

from .scan import CLASSES as SCAN_CLASSES
from .validate import CLASSES as VALIDATE_CLASSES
from .export import CLASSES as EXPORT_CLASSES
from .groups import CLASSES as GROUP_CLASSES
from .presets import CLASSES as PRESET_CLASSES
from .outliner import CLASSES as OUTLINER_CLASSES
from .photoshop import CLASSES as PHOTOSHOP_CLASSES
from .isolation import CLASSES as ISOLATION_CLASSES

CLASSES = (*SCAN_CLASSES, *VALIDATE_CLASSES, *GROUP_CLASSES, *PRESET_CLASSES,
           *OUTLINER_CLASSES, *EXPORT_CLASSES, *PHOTOSHOP_CLASSES,
           *ISOLATION_CLASSES)
