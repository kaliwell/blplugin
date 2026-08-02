import os
import re

import bpy


INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL",
                    *(f"COM{index}" for index in range(1, 10)),
                    *(f"LPT{index}" for index in range(1, 10))}


class OutputTemplateError(ValueError):
    pass


def safe_filename(value):
    cleaned = INVALID_FILENAME.sub("_", value).strip().rstrip(".")
    cleaned = cleaned or "untitled"
    if cleaned.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        cleaned = "_" + cleaned
    return cleaned


def format_output_name(scene, settings, collection, mode, extension=None):
    values = {
        "blend": blend_stem(),
        "scene": scene.name,
        "camera": scene.camera.name if scene.camera else "no_camera",
        "collection": collection,
        "frame": f"{scene.frame_current:04d}",
        "mode": mode.lower(),
    }
    template = settings.filename_template or "{blend}_{collection}_{mode}"
    try:
        rendered = template.format_map(values)
    except (KeyError, ValueError) as exc:
        raise OutputTemplateError(f"无效命名模板：{exc}") from exc
    if extension is None:
        extension = ".exr" if settings.output_format == "OPEN_EXR" else ".png"
    return safe_filename(rendered) + extension


def resolved_output_root(scene, settings):
    raw = settings.output_directory or "//CMask_Output/"
    return os.path.abspath(bpy.path.abspath(raw, library=scene.library))


def ensure_output_dirs(scene, settings):
    root = resolved_output_root(scene, settings)
    color_dir = os.path.join(root, "Color_ID")
    mask_dir = os.path.join(root, "Masks")
    os.makedirs(color_dir, exist_ok=True)
    os.makedirs(mask_dir, exist_ok=True)
    return root, color_dir, mask_dir


def blend_stem():
    if not bpy.data.filepath:
        return "untitled"
    return safe_filename(os.path.splitext(os.path.basename(bpy.data.filepath))[0])


def color_id_path(scene, settings):
    _, color_dir, _ = ensure_output_dirs(scene, settings)
    return os.path.join(color_dir, format_output_name(
        scene, settings, "collections", "color_id"
    ))


def mask_path(scene, settings, collection_name):
    _, _, mask_dir = ensure_output_dirs(scene, settings)
    return os.path.join(mask_dir, format_output_name(
        scene, settings, collection_name, settings.mask_output_mode
    ))


def multilayer_path(scene, settings):
    root, _color_dir, _mask_dir = ensure_output_dirs(scene, settings)
    return os.path.join(root, format_output_name(
        scene, settings, "all_masks", "multilayer", extension=".exr"
    ))


def cryptomatte_path(scene, settings):
    root, _color_dir, _mask_dir = ensure_output_dirs(scene, settings)
    return os.path.join(root, format_output_name(
        scene, settings, "collections", "cryptomatte", extension=".exr"
    ))


def unique_mask_paths(scene, settings, items):
    """Return stable, non-colliding paths for one batch export."""
    used = set()
    results = []
    for item in items:
        path = mask_path(scene, settings, item.collection.name)
        key = os.path.normcase(os.path.abspath(path))
        if key in used:
            stem, extension = os.path.splitext(path)
            identifier = str(item.collection.get("cmask_uuid", ""))[:8]
            suffix = safe_filename(identifier) if identifier else "2"
            candidate = f"{stem}_{suffix}{extension}"
            counter = 2
            while os.path.normcase(os.path.abspath(candidate)) in used:
                candidate = f"{stem}_{suffix}_{counter}{extension}"
                counter += 1
            path = candidate
            key = os.path.normcase(os.path.abspath(path))
        used.add(key)
        results.append((item, path))
    return results


def disambiguate_path(path, used, suffix):
    key = os.path.normcase(os.path.abspath(path))
    if key not in used:
        used.add(key)
        return path
    stem, extension = os.path.splitext(path)
    cleaned_suffix = safe_filename(suffix)
    candidate = f"{stem}_{cleaned_suffix}{extension}"
    counter = 2
    while os.path.normcase(os.path.abspath(candidate)) in used:
        candidate = f"{stem}_{cleaned_suffix}_{counter}{extension}"
        counter += 1
    used.add(os.path.normcase(os.path.abspath(candidate)))
    return candidate
