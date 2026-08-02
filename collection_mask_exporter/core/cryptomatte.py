import json
import os
import struct


def _rotl32(value, amount):
    return ((value << amount) | (value >> (32 - amount))) & 0xFFFFFFFF


def murmurhash3_32(value):
    """Return the Cryptomatte-standard MurmurHash3 x86 32-bit hash."""
    data = value.encode("utf-8") if isinstance(value, str) else bytes(value)
    length = len(data)
    result = 0
    c1 = 0xCC9E2D51
    c2 = 0x1B873593

    for offset in range(0, length - (length % 4), 4):
        block = int.from_bytes(data[offset:offset + 4], "little")
        block = (block * c1) & 0xFFFFFFFF
        block = _rotl32(block, 15)
        block = (block * c2) & 0xFFFFFFFF
        result ^= block
        result = _rotl32(result, 13)
        result = (result * 5 + 0xE6546B64) & 0xFFFFFFFF

    tail = data[length - (length % 4):]
    block = 0
    if len(tail) == 3:
        block ^= tail[2] << 16
    if len(tail) >= 2:
        block ^= tail[1] << 8
    if tail:
        block ^= tail[0]
        block = (block * c1) & 0xFFFFFFFF
        block = _rotl32(block, 15)
        block = (block * c2) & 0xFFFFFFFF
        result ^= block

    result ^= length
    result ^= result >> 16
    result = (result * 0x85EBCA6B) & 0xFFFFFFFF
    result ^= result >> 13
    result = (result * 0xC2B2AE35) & 0xFFFFFFFF
    result ^= result >> 16
    return result & 0xFFFFFFFF


def cryptomatte_hash(value):
    """Return the adjusted uint32, float ID and manifest hex value."""
    bits = murmurhash3_32(value)
    exponent = (bits >> 23) & 0xFF
    if exponent in {0, 0xFF}:
        bits ^= 1 << 23
    float_id = struct.unpack("<f", struct.pack("<I", bits))[0]
    return bits, float_id, f"{bits:08x}"


def _alpha_channel(spec):
    if spec.alpha_channel >= 0:
        return spec.alpha_channel
    for index, name in enumerate(spec.channelnames):
        if name == "A" or name.rsplit(".", 1)[-1] == "A":
            return index
    raise RuntimeError("Cryptomatte 临时蒙版缺少 Alpha 通道")


def combine_collection_cryptomatte(output_path, masks, depth=6,
                                   layer_name="CryptoCollection"):
    """Pack Collection mask alpha into standard Cryptomatte ID/coverage layers."""
    try:
        import OpenImageIO as oiio
        import numpy
    except ImportError as exc:
        raise RuntimeError("当前 Blender 缺少 OpenImageIO，无法写入 Cryptomatte") from exc
    if not masks:
        raise ValueError("没有可写入 Cryptomatte 的 Collection 蒙版")
    depth = int(depth)
    if depth < 2 or depth > 12 or depth % 2:
        raise ValueError("Cryptomatte 深度必须是 2 到 12 之间的偶数")

    inputs = []
    output = None
    try:
        width = height = None
        for name, path in masks:
            image_input = oiio.ImageInput.open(path)
            if not image_input:
                raise RuntimeError(f"无法读取 Cryptomatte 临时蒙版：{path}")
            spec = image_input.spec()
            if width is None:
                width, height = spec.width, spec.height
            elif (spec.width, spec.height) != (width, height):
                image_input.close()
                raise RuntimeError("Cryptomatte 临时蒙版尺寸不一致")
            inputs.append((name, image_input, _alpha_channel(spec)))

        crypto_layers = depth // 2
        channel_names = [
            f"{layer_name}{index:02d}.{channel}"
            for index in range(crypto_layers)
            for channel in ("R", "G", "B", "A")
        ]
        spec = oiio.ImageSpec(width, height, len(channel_names), oiio.FLOAT)
        spec.channelnames = channel_names
        spec.attribute("compression", "zip")
        spec.attribute("Software", "Collection Mask Exporter")

        manifest = {}
        float_ids = []
        for name, _image_input, _alpha in inputs:
            _bits, float_id, hex_id = cryptomatte_hash(name)
            manifest[name] = hex_id
            float_ids.append(float_id)
        metadata_id = cryptomatte_hash(layer_name)[2][:-1]
        prefix = f"cryptomatte/{metadata_id}/"
        spec.attribute(prefix + "name", layer_name)
        spec.attribute(prefix + "hash", "MurmurHash3_32")
        spec.attribute(prefix + "conversion", "uint32_to_float32")
        spec.attribute(
            prefix + "manifest",
            json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        output = oiio.ImageOutput.create(output_path)
        if not output or not output.open(output_path, spec):
            error = output.geterror() if output else "无法创建输出插件"
            raise RuntimeError(f"无法创建 Cryptomatte EXR：{error}")

        float_ids = numpy.asarray(float_ids, dtype=numpy.float32)
        for y in range(height):
            coverage_rows = []
            for _name, image_input, alpha_index in inputs:
                row = image_input.read_scanline(y, 0, oiio.FLOAT)
                if row is None:
                    raise RuntimeError(
                        f"读取 Cryptomatte 临时蒙版失败：{image_input.geterror()}"
                    )
                coverage_rows.append(row[:, alpha_index])
            coverages = numpy.stack(coverage_rows, axis=0)
            order = numpy.argsort(-coverages, axis=0, kind="stable")
            packed = numpy.zeros((width, len(channel_names)), dtype=numpy.float32)
            for rank in range(min(depth, len(inputs))):
                indices = order[rank]
                values = numpy.take_along_axis(
                    coverages, indices[numpy.newaxis, :], axis=0
                )[0]
                channel = (rank // 2) * 4 + (rank % 2) * 2
                packed[:, channel] = numpy.where(values > 0.0, float_ids[indices], 0.0)
                packed[:, channel + 1] = values
            if not output.write_scanline(y, 0, packed):
                raise RuntimeError(f"写入 Cryptomatte EXR 失败：{output.geterror()}")
        if not output.close():
            raise RuntimeError(f"关闭 Cryptomatte EXR 失败：{output.geterror()}")
        output = None
        return manifest
    finally:
        if output:
            output.close()
        for _name, image_input, _alpha in inputs:
            image_input.close()
