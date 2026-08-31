# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

from array import array
import bpy
import numpy as np


def _morph_alpha_array(alpha, width, height, amount):
    radius = abs(int(amount))
    source = np.asarray(alpha, dtype=np.float32).reshape(height, width)
    if radius == 0:
        return source
    window = radius * 2 + 1
    reducer = np.max if amount > 0 else np.min
    horizontal_source = np.pad(
        source, ((0, 0), (radius, radius)),
        mode="constant", constant_values=0.0,
    )
    horizontal_windows = np.lib.stride_tricks.sliding_window_view(
        horizontal_source, window_shape=window, axis=1,
    )
    horizontal = reducer(horizontal_windows, axis=-1)
    vertical_source = np.pad(
        horizontal, ((radius, radius), (0, 0)),
        mode="constant", constant_values=0.0,
    )
    vertical_windows = np.lib.stride_tricks.sliding_window_view(
        vertical_source, window_shape=window, axis=0,
    )
    return np.ascontiguousarray(reducer(vertical_windows, axis=-1))


def morph_alpha(alpha, width, height, amount):
    return _morph_alpha_array(
        alpha, width, height, amount
    ).reshape(-1).tolist()


def apply_mask_postprocess(scene, filepath, amount, alpha_mode, preview=False,
                           color=(1.0, 1.0, 1.0, 1.0)):
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
        rgba = np.frombuffer(pixels, dtype=np.float32).reshape(-1, 4)
        alpha = rgba[:, 3].reshape(height, width)
        strongest = int(np.argmax(alpha))
        rendered_color = (
            rgba[strongest, :3].copy()
            if rgba[strongest, 3] > 0.0
            else np.asarray(color[:3], dtype=np.float32)
        )
        adjusted = _morph_alpha_array(alpha, width, height, amount)
        flat_alpha = adjusted.reshape(-1)
        if alpha_mode == "PREMULTIPLIED":
            rgba[:, :3] = flat_alpha[:, None] * rendered_color[None, :]
        else:
            rgba[:, :3] = rendered_color
        rgba[:, 3] = flat_alpha
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
