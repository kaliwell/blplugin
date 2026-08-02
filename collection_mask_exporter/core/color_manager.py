import colorsys
import uuid

from ..constants import PALETTE


def ensure_uuid(collection):
    value = collection.get("cmask_uuid")
    if not value:
        value = str(uuid.uuid4())
        collection["cmask_uuid"] = value
    return value


def generated_color(index):
    if index < len(PALETTE):
        return PALETTE[index]
    # Golden-ratio spacing avoids adjacent hues clustering together.
    hue = (0.11 + index * 0.618033988749895) % 1.0
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.88, 1.0)
    return (red, green, blue, 1.0)


def ensure_color(collection, index):
    stored = collection.get("cmask_color")
    if stored is None or len(stored) not in {3, 4}:
        stored = generated_color(index)
        collection["cmask_color"] = list(stored)
    values = tuple(float(value) for value in stored)
    return values if len(values) == 4 else (*values, 1.0)


def ensure_metadata(collection, index):
    ensure_uuid(collection)
    color = ensure_color(collection, index)
    if "cmask_role" not in collection:
        collection["cmask_role"] = "MASK"
    if "cmask_enabled" not in collection:
        collection["cmask_enabled"] = True
    if "cmask_priority" not in collection:
        collection["cmask_priority"] = index
    return color
