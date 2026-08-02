import os
import re


INVALID_LAYER = re.compile(r"[^\w\-]+", re.UNICODE)


def safe_layer_name(value):
    cleaned = INVALID_LAYER.sub("_", value).strip("_")
    return cleaned or "Mask"


def combine_multilayer_exr(output_path, layers, half_float=True):
    try:
        import OpenImageIO as oiio
        import numpy
    except ImportError as exc:
        raise RuntimeError("当前 Blender 缺少 OpenImageIO，无法写入多层 EXR") from exc
    if not layers:
        raise ValueError("没有可写入多层 EXR 的图层")

    inputs = []
    output = None
    try:
        width = height = None
        used = set()
        resolved = []
        for requested_name, path in layers:
            image_input = oiio.ImageInput.open(path)
            if not image_input:
                raise RuntimeError(f"无法读取临时 EXR：{path}")
            spec = image_input.spec()
            if spec.nchannels < 4:
                image_input.close()
                raise RuntimeError(f"临时 EXR 缺少 RGBA 通道：{path}")
            if width is None:
                width, height = spec.width, spec.height
            elif (spec.width, spec.height) != (width, height):
                image_input.close()
                raise RuntimeError("多层 EXR 的输入图像尺寸不一致")

            base = safe_layer_name(requested_name)
            name = base
            counter = 2
            while name.casefold() in used:
                name = f"{base}_{counter}"
                counter += 1
            used.add(name.casefold())
            inputs.append(image_input)
            resolved.append((name, path))

        channel_names = [
            f"{name}.{channel}"
            for name, _path in resolved
            for channel in ("R", "G", "B", "A")
        ]
        data_type = oiio.HALF if half_float else oiio.FLOAT
        output_spec = oiio.ImageSpec(width, height, len(channel_names), data_type)
        output_spec.channelnames = channel_names
        output_spec.attribute("compression", "zip")
        output_spec.attribute("Software", "Collection Mask Exporter")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        output = oiio.ImageOutput.create(output_path)
        if not output or not output.open(output_path, output_spec):
            error = output.geterror() if output else "无法创建输出插件"
            raise RuntimeError(f"无法创建多层 EXR：{error}")

        for y in range(height):
            rows = []
            for image_input in inputs:
                row = image_input.read_scanline(y, 0, oiio.FLOAT)
                if row is None:
                    raise RuntimeError(f"读取 EXR 扫描线失败：{image_input.geterror()}")
                rows.append(row[:, :4])
            combined = numpy.concatenate(rows, axis=1)
            if not output.write_scanline(y, 0, combined):
                raise RuntimeError(f"写入 EXR 扫描线失败：{output.geterror()}")
        if not output.close():
            raise RuntimeError(f"关闭多层 EXR 失败：{output.geterror()}")
        output = None
        return resolved
    finally:
        if output:
            output.close()
        for image_input in inputs:
            image_input.close()
