import os

import bpy


GENERATED_KEY = "cmask_generated"


def get_compositor_tree(scene, create=False):
    if hasattr(scene, "node_tree"):
        if create:
            scene.use_nodes = True
        return scene.node_tree
    tree = getattr(scene, "compositing_node_group", None)
    if tree is None and create:
        tree = bpy.data.node_groups.new(
            f"CMask Compositor - {scene.name}", "CompositorNodeTree"
        )
        scene.compositing_node_group = tree
    return tree


def create_compositor_image_nodes(scene, paths):
    existing_paths = [os.path.abspath(path) for path in paths if os.path.isfile(path)]
    if not existing_paths:
        raise RuntimeError("最近输出中没有可读取的图像")
    tree = get_compositor_tree(scene, create=True)
    if tree is None:
        raise RuntimeError("无法创建场景合成节点树")

    for node in list(tree.nodes):
        if node.get(GENERATED_KEY):
            tree.nodes.remove(node)

    frame = tree.nodes.new("NodeFrame")
    frame.name = "CMask Imported Outputs"
    frame.label = "CMask 最近输出"
    frame[GENERATED_KEY] = True

    created = []
    columns = 4
    for index, path in enumerate(existing_paths):
        image = bpy.data.images.load(path, check_existing=True)
        node = tree.nodes.new("CompositorNodeImage")
        node.image = image
        node.name = f"CMask {os.path.basename(path)}"
        node.label = os.path.basename(path)
        node.location = ((index % columns) * 260, -(index // columns) * 220)
        node.parent = frame
        node[GENERATED_KEY] = True
        created.append(node)
    return created
