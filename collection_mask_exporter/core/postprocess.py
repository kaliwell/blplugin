from array import array
from collections import deque

import bpy


def _filter_line(values, radius, maximum):
    if radius <= 0:
        return list(values)
    outside = 0.0
    padded = [outside] * radius + list(values) + [outside] * radius
    window = radius * 2 + 1
    queue = deque()
    result = []
    for index, value in enumerate(padded):
        while queue and queue[0] <= index - window:
            queue.popleft()
        if maximum:
            while queue and padded[queue[-1]] <= value:
                queue.pop()
        else:
            while queue and padded[queue[-1]] >= value:
                queue.pop()
        queue.append(index)
        if index >= window - 1:
            result.append(padded[queue[0]])
    return result


def morph_alpha(alpha, width, height, amount):
    radius = abs(int(amount))
    if radius == 0:
        return list(alpha)
    maximum = amount > 0
    horizontal = [0.0] * (width * height)
    for y in range(height):
        start = y * width
        horizontal[start:start + width] = _filter_line(
            alpha[start:start + width], radius, maximum
        )
    result = [0.0] * (width * height)
    for x in range(width):
        column = [horizontal[y * width + x] for y in range(height)]
        filtered = _filter_line(column, radius, maximum)
        for y, value in enumerate(filtered):
            result[y * width + x] = value
    return result


def apply_mask_postprocess(scene, filepath, amount, alpha_mode, preview=False):
    loaded = False
    if preview or not filepath:
        image = bpy.data.images.get("Render Result")
    else:
        image = bpy.data.images.load(filepath, check_existing=False)
        loaded = True
    if image is None or image.size[0] == 0 or image.size[1] == 0:
        raise RuntimeError("无法读取蒙版图像进行边缘处理")
    try:
        width, height = image.size
        pixels = array("f", [0.0]) * len(image.pixels)
        image.pixels.foreach_get(pixels)
        alpha = pixels[3::4]
        adjusted = morph_alpha(alpha, width, height, amount) if amount else alpha
        for index, value in enumerate(adjusted):
            offset = index * 4
            color = value if alpha_mode == "PREMULTIPLIED" else 1.0
            pixels[offset] = color
            pixels[offset + 1] = color
            pixels[offset + 2] = color
            pixels[offset + 3] = value
        image.pixels.foreach_set(pixels)
        image.update()
        if filepath:
            image.save_render(filepath, scene=scene)
    finally:
        if loaded:
            bpy.data.images.remove(image)


def apply_edge_adjustment(scene, filepath, amount, preview=False):
    """Backward-compatible wrapper for callers from v0.3.0."""
    if amount:
        apply_mask_postprocess(scene, filepath, amount, "STRAIGHT", preview)
