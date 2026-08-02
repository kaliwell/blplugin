# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import os


def _linear_to_srgb(value):
    value = max(0.0, min(1.0, float(value)))
    if value <= 0.0031308:
        return value * 12.92
    return 1.055 * (value ** (1.0 / 2.4)) - 0.055


def combine_color_id(output_path, masks, output_format="PNG", color_depth="8"):
    """Combine non-overlapping visible masks into one straight-alpha color ID."""
    try:
        import OpenImageIO as oiio
        import numpy
    except ImportError as exc:
        raise RuntimeError("当前 Blender 缺少 OpenImageIO，无法拆分 Geometry Nodes ID") from exc
    if not masks:
        raise ValueError("没有可合并的 CMask 蒙版")

    inputs = []
    output = None
    try:
        width = height = None
        colors = []
        for color, path in masks:
            image_input = oiio.ImageInput.open(path)
            if not image_input:
                raise RuntimeError(f"无法读取临时蒙版：{path}")
            spec = image_input.spec()
            alpha = spec.alpha_channel
            if alpha < 0:
                alpha = next((index for index, name in enumerate(spec.channelnames)
                              if name == "A" or name.rsplit(".", 1)[-1] == "A"), -1)
            if alpha < 0:
                image_input.close()
                raise RuntimeError(f"临时蒙版缺少 Alpha 通道：{path}")
            if width is None:
                width, height = spec.width, spec.height
            elif (spec.width, spec.height) != (width, height):
                image_input.close()
                raise RuntimeError("临时蒙版尺寸不一致")
            inputs.append((image_input, alpha))
            rgb = tuple(float(value) for value in color[:3])
            if output_format == "PNG":
                rgb = tuple(_linear_to_srgb(value) for value in rgb)
            colors.append(rgb)

        if output_format == "OPEN_EXR":
            data_type = oiio.FLOAT if color_depth == "32" else oiio.HALF
        else:
            data_type = oiio.UINT16 if color_depth == "16" else oiio.UINT8
        spec = oiio.ImageSpec(width, height, 4, data_type)
        spec.channelnames = ["R", "G", "B", "A"]
        spec.alpha_channel = 3
        spec.attribute("Software", "Collection Mask Exporter")
        if output_format == "PNG":
            spec.attribute("oiio:ColorSpace", "sRGB")
        else:
            spec.attribute("compression", "zip")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        output = oiio.ImageOutput.create(output_path)
        if not output or not output.open(output_path, spec):
            error = output.geterror() if output else "无法创建输出插件"
            raise RuntimeError(f"无法创建拆分彩色 ID：{error}")

        colors = numpy.asarray(colors, dtype=numpy.float32)
        for y in range(height):
            coverages = []
            for image_input, alpha in inputs:
                row = image_input.read_scanline(y, 0, oiio.FLOAT)
                if row is None:
                    raise RuntimeError(f"读取临时蒙版失败：{image_input.geterror()}")
                coverages.append(row[:, alpha])
            coverage = numpy.stack(coverages, axis=0)
            owner = numpy.argmax(coverage, axis=0)
            maximum = numpy.max(coverage, axis=0)
            row = numpy.zeros((width, 4), dtype=numpy.float32)
            visible = maximum > 0.0
            row[visible, :3] = colors[owner[visible]]
            row[:, 3] = maximum
            if not output.write_scanline(y, 0, row):
                raise RuntimeError(f"写入拆分彩色 ID 失败：{output.geterror()}")
        if not output.close():
            raise RuntimeError(f"关闭拆分彩色 ID 失败：{output.geterror()}")
        output = None
        return output_path
    finally:
        if output:
            output.close()
        for image_input, _alpha in inputs:
            image_input.close()
