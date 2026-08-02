# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import uuid


ID_MATERIAL_NAME = "__CMASK_MATERIAL_ID"
WHITE_MATERIAL_NAME = "__CMASK_MATERIAL_WHITE"
MASK_MATERIAL_NAME = "__CMASK_MATERIAL_MASK"


def ensure_material_node_tree(material):
    """Return a shader tree without touching deprecated 5.x state unnecessarily."""
    tree = material.node_tree
    if tree is None:
        # Blender 4.x creates the tree lazily. Blender 5.2 creates it by
        # default and deprecates assigning use_nodes ahead of Blender 6.0.
        material.use_nodes = True
        tree = material.node_tree
    if tree is None:
        raise RuntimeError("无法为临时材质创建节点树")
    return tree


def _new_emission_material(prefix, use_object_color, fixed_color=None):
    name = f"{prefix}_{uuid.uuid4().hex}"
    material = bpy.data.materials.new(name)
    tree = ensure_material_node_tree(material)
    nodes = tree.nodes
    links = tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0
    if use_object_color:
        info = nodes.new("ShaderNodeObjectInfo")
        links.new(info.outputs["Color"], emission.inputs["Color"])
    else:
        emission.inputs["Color"].default_value = tuple(
            fixed_color or (1.0, 1.0, 1.0, 1.0)
        )
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def get_id_material():
    return _new_emission_material(ID_MATERIAL_NAME, True)


def get_white_material():
    return _new_emission_material(WHITE_MATERIAL_NAME, False)


def get_mask_material(color):
    return _new_emission_material(MASK_MATERIAL_NAME, False, color)


def remove_temp_material(material):
    if material and material.name in bpy.data.materials and material.users == 0:
        bpy.data.materials.remove(material)
        return True
    return material is None or material.name not in bpy.data.materials
