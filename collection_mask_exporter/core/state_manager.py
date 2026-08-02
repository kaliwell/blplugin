from dataclasses import dataclass

import bpy


@dataclass
class SceneState:
    engine: str
    filepath: str
    film_transparent: bool
    file_format: str
    color_mode: str
    color_depth: str
    view_transform: str
    exposure: float
    gamma: float
    use_compositing: bool
    use_sequencer: bool
    object_states: list
    active_view_layer: tuple
    view_layer_uses: list
    data_materials: list


def capture_scene_state(context, extra_objects=()):
    scene = context.scene
    image = scene.render.image_settings
    objects = list(scene.objects)
    seen = set(objects)
    for obj in extra_objects:
        if obj not in seen:
            seen.add(obj)
            objects.append(obj)
    return SceneState(
        engine=scene.render.engine,
        filepath=scene.render.filepath,
        film_transparent=scene.render.film_transparent,
        file_format=image.file_format,
        color_mode=image.color_mode,
        color_depth=image.color_depth,
        view_transform=scene.view_settings.view_transform,
        exposure=scene.view_settings.exposure,
        gamma=scene.view_settings.gamma,
        use_compositing=scene.render.use_compositing,
        use_sequencer=scene.render.use_sequencer,
        object_states=[
            (obj.name, obj.as_pointer(), tuple(obj.color),
             bool(obj.hide_render), bool(obj.is_holdout))
            for obj in objects
        ],
        active_view_layer=(
            (context.window.view_layer.name,
             context.window.view_layer.as_pointer())
            if context.window else None
        ),
        view_layer_uses=[
            (layer.name, layer.as_pointer(), bool(layer.use))
            for layer in scene.view_layers
        ],
        data_materials=[
            (obj.data, obj.data.name, obj.data.as_pointer(), tuple(obj.data.materials))
            for obj in objects
            if obj.data is not None and hasattr(obj.data, "materials")
        ],
    )


def restore_scene_state(context, state):
    scene = context.scene
    errors = []

    def attempt(label, callback):
        try:
            callback()
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    settings = (
        ("渲染引擎", lambda: setattr(scene.render, "engine", state.engine)),
        ("输出路径", lambda: setattr(scene.render, "filepath", state.filepath)),
        ("透明背景", lambda: setattr(scene.render, "film_transparent", state.film_transparent)),
        ("文件格式", lambda: setattr(scene.render.image_settings, "file_format", state.file_format)),
        ("颜色模式", lambda: setattr(scene.render.image_settings, "color_mode", state.color_mode)),
        ("位深", lambda: setattr(scene.render.image_settings, "color_depth", state.color_depth)),
        ("视图变换", lambda: setattr(scene.view_settings, "view_transform", state.view_transform)),
        ("曝光", lambda: setattr(scene.view_settings, "exposure", state.exposure)),
        ("Gamma", lambda: setattr(scene.view_settings, "gamma", state.gamma)),
        ("合成器", lambda: setattr(scene.render, "use_compositing", state.use_compositing)),
        ("序列器", lambda: setattr(scene.render, "use_sequencer", state.use_sequencer)),
    )
    for label, callback in settings:
        attempt(label, callback)

    for name, pointer, color, hide_render, is_holdout in state.object_states:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.as_pointer() != pointer:
            continue
        attempt(f"对象 {name}", lambda obj=obj, color=color,
                hide_render=hide_render, is_holdout=is_holdout: (
                    setattr(obj, "color", color),
                    setattr(obj, "hide_render", hide_render),
                    setattr(obj, "is_holdout", is_holdout),
                ))

    for name, pointer, use in state.view_layer_uses:
        layer = scene.view_layers.get(name)
        if layer is None or layer.as_pointer() != pointer:
            continue
        attempt(f"View Layer {name}", lambda layer=layer, use=use:
                setattr(layer, "use", use))

    for data, name, pointer, materials in state.data_materials:
        try:
            if data.as_pointer() != pointer:
                continue
            slots = data.materials
            slots.clear()
            for material in materials:
                slots.append(material)
        except Exception as exc:
            errors.append(f"数据材质 {name}: {exc}")

    if context.window and state.active_view_layer:
        name, pointer = state.active_view_layer
        layer = scene.view_layers.get(name)
        if layer is not None and layer.as_pointer() == pointer:
            attempt("活动 View Layer", lambda: setattr(context.window, "view_layer", layer))
    return errors
