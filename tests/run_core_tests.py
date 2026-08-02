# SPDX-FileCopyrightText: 2026 kaliwill
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import pathlib
import sys

import bpy

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

addon = importlib.import_module("collection_mask_exporter")
addon.register()


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Factory reset unregisters runtime classes in some Blender versions.
    if not hasattr(bpy.types.Scene, "cmask_settings"):
        addon.register()
    return bpy.context.scene


def add_mesh(collection, name):
    mesh = bpy.data.meshes.new(name + "Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def test_scan_and_stable_color():
    scene = reset_scene()
    first = bpy.data.collections.new("CM_First")
    second = bpy.data.collections.new("Other")
    scene.collection.children.link(first)
    scene.collection.children.link(second)
    add_mesh(first, "FirstObject")
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    assert len(settings.groups) == 1
    old_uuid = first["cmask_uuid"]
    old_color = tuple(first["cmask_color"])
    first.name = "CM_Renamed"
    bpy.ops.cmask.scan()
    assert first["cmask_uuid"] == old_uuid
    assert tuple(first["cmask_color"]) == old_color


def test_nested_explicit_child_wins():
    from collection_mask_exporter.core.group_resolver import resolve_groups
    scene = reset_scene()
    parent = bpy.data.collections.new("CM_Parent")
    child = bpy.data.collections.new("CM_Child")
    scene.collection.children.link(parent)
    parent.children.link(child)
    parent_obj = add_mesh(parent, "ParentObject")
    child_obj = add_mesh(child, "ChildObject")
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    result = resolve_groups(settings.groups, True)
    assert result.assignments[parent_obj].collection == parent
    assert result.assignments[child_obj].collection == child
    assert child_obj not in result.conflicts


def test_multiple_membership_conflict():
    from collection_mask_exporter.core.conflict_checker import validate_groups
    scene = reset_scene()
    first = bpy.data.collections.new("CM_First")
    second = bpy.data.collections.new("CM_Second")
    scene.collection.children.link(first)
    scene.collection.children.link(second)
    obj = add_mesh(first, "Shared")
    second.objects.link(obj)
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    issues, result = validate_groups(settings)
    assert obj in result.conflicts
    assert any(issue.code == "MULTIPLE_MEMBERSHIP" for issue in issues)
    assert result.assignments[obj].collection == first


def test_scan_preserves_role_and_enabled_state():
    scene = reset_scene()
    collection = bpy.data.collections.new("CM_Holdout")
    scene.collection.children.link(collection)
    collection["cmask_role"] = "HOLDOUT"
    collection["cmask_enabled"] = False
    collection["cmask_color"] = [0.2, 0.3, 0.4, 1.0]
    bpy.ops.cmask.scan()
    item = scene.cmask_settings.groups[0]
    assert item.role == "HOLDOUT"
    assert item.enabled is False
    assert collection["cmask_role"] == "HOLDOUT"


def test_scan_current_view_layer_visibility():
    from collection_mask_exporter.core.layer_collection import collection_layer_map

    scene = reset_scene()
    visible = bpy.data.collections.new("CM_Visible")
    excluded = bpy.data.collections.new("CM_Excluded")
    hidden = bpy.data.collections.new("CM_Hidden")
    nested = bpy.data.collections.new("CM_NestedUnderExcluded")
    scene.collection.children.link(visible)
    scene.collection.children.link(excluded)
    scene.collection.children.link(hidden)
    excluded.children.link(nested)

    mapping = collection_layer_map(bpy.context.view_layer)
    mapping[excluded].exclude = True
    mapping[hidden].hide_viewport = True
    settings = scene.cmask_settings
    settings.scan_visible_only = True
    bpy.ops.cmask.scan()
    assert [item.collection for item in settings.groups] == [visible]

    settings.scan_visible_only = False
    bpy.ops.cmask.scan()
    assert {item.collection for item in settings.groups} == {
        visible, excluded, hidden, nested,
    }


def test_explicit_grandchild_wins_through_implicit_parent():
    from collection_mask_exporter.core.group_resolver import resolve_groups
    scene = reset_scene()
    parent = bpy.data.collections.new("CM_Parent")
    middle = bpy.data.collections.new("Middle")
    grandchild = bpy.data.collections.new("CM_Grandchild")
    scene.collection.children.link(parent)
    parent.children.link(middle)
    middle.children.link(grandchild)
    obj = add_mesh(grandchild, "DeepObject")
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    result = resolve_groups(settings.groups, True)
    assert result.assignments[obj].collection == grandchild
    assert obj not in result.conflicts


def test_nested_collection_instance_is_renderable_host():
    from collection_mask_exporter.core.conflict_checker import validate_groups
    from collection_mask_exporter.core.group_resolver import resolve_groups
    from collection_mask_exporter.core.scanner import renderable_objects

    scene = reset_scene()
    group = bpy.data.collections.new("CM_InstanceHost")
    outer_source = bpy.data.collections.new("OuterInstanceSource")
    inner_source = bpy.data.collections.new("InnerInstanceSource")
    scene.collection.children.link(group)
    add_mesh(inner_source, "DeepInstanceMesh")

    nested_host = bpy.data.objects.new("NestedInstance", None)
    nested_host.instance_type = "COLLECTION"
    nested_host.instance_collection = inner_source
    outer_source.objects.link(nested_host)

    host = bpy.data.objects.new("CollectionInstance", None)
    host.instance_type = "COLLECTION"
    host.instance_collection = outer_source
    group.objects.link(host)

    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    assert renderable_objects(group) == [host]
    resolution = resolve_groups(settings.groups, True)
    assert resolution.assignments[host].collection == group
    assert nested_host in resolution.instance_sources[host]
    assert next(iter(inner_source.objects)) in resolution.instance_sources[host]
    issues, _resolution = validate_groups(settings)
    assert not any(issue.code == "EMPTY" for issue in issues)


def test_collection_instance_source_group_conflict():
    from collection_mask_exporter.core.conflict_checker import validate_groups

    scene = reset_scene()
    host_group = bpy.data.collections.new("CM_Host")
    source_group = bpy.data.collections.new("CM_Source")
    scene.collection.children.link(host_group)
    scene.collection.children.link(source_group)
    add_mesh(source_group, "SourceMesh")
    host = bpy.data.objects.new("InstanceHost", None)
    host.instance_type = "COLLECTION"
    host.instance_collection = source_group
    host_group.objects.link(host)
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    issues, _resolution = validate_groups(settings)
    issue = next(item for item in issues if item.code == "INSTANCE_SOURCE_GROUP")
    assert issue.level == "WARNING" and "CM_Source" in issue.message
    settings.conflict_mode = "STRICT"
    issues, _resolution = validate_groups(settings)
    assert next(item for item in issues
                if item.code == "INSTANCE_SOURCE_GROUP").level == "ERROR"


def test_geometry_nodes_source_resolution():
    from collection_mask_exporter.core.conflict_checker import validate_groups
    from collection_mask_exporter.core.geometry_nodes import geometry_node_dependencies

    scene = reset_scene()
    host_group = bpy.data.collections.new("CM_GeometryHost")
    source_group = bpy.data.collections.new("CM_GeometrySource")
    nested_used_group = bpy.data.collections.new("GeometryNestedUsed")
    unused_group = bpy.data.collections.new("GeometryUnusedSource")
    scene.collection.children.link(host_group)
    scene.collection.children.link(source_group)
    scene.collection.children.link(nested_used_group)
    scene.collection.children.link(unused_group)
    host = add_mesh(host_group, "GeometryHost")
    source = add_mesh(source_group, "GeometrySource")
    nested_used_source = add_mesh(nested_used_group, "GeometryNestedUsed")
    unused_source = add_mesh(unused_group, "GeometryUnusedSource")
    tree = bpy.data.node_groups.new("CMaskGeometryTest", "GeometryNodeTree")
    if bpy.app.version >= (4, 0, 0):
        tree.interface.new_socket(
            name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
        )
        tree.interface.new_socket(
            name="Dynamic Collection", in_out="INPUT",
            socket_type="NodeSocketCollection",
        )
    else:
        tree.outputs.new("NodeSocketGeometry", "Geometry")
        tree.inputs.new("NodeSocketCollection", "Dynamic Collection")
    output = tree.nodes.new("NodeGroupOutput")
    info = tree.nodes.new("GeometryNodeCollectionInfo")
    info.inputs["Collection"].default_value = source_group
    dynamic_info = tree.nodes.new("GeometryNodeCollectionInfo")
    group_input = tree.nodes.new("NodeGroupInput")
    tree.links.new(
        group_input.outputs["Dynamic Collection"],
        dynamic_info.inputs["Collection"],
    )
    join = tree.nodes.new("GeometryNodeJoinGeometry")
    tree.links.new(info.outputs["Instances"], join.inputs["Geometry"])
    tree.links.new(dynamic_info.outputs["Instances"], join.inputs["Geometry"])

    nested_tree = bpy.data.node_groups.new("CMaskNestedOutputTest", "GeometryNodeTree")
    if bpy.app.version >= (4, 0, 0):
        nested_tree.interface.new_socket(
            name="Used", in_out="OUTPUT", socket_type="NodeSocketGeometry"
        )
        nested_tree.interface.new_socket(
            name="Unused", in_out="OUTPUT", socket_type="NodeSocketGeometry"
        )
    else:
        nested_tree.outputs.new("NodeSocketGeometry", "Used")
        nested_tree.outputs.new("NodeSocketGeometry", "Unused")
    nested_output = nested_tree.nodes.new("NodeGroupOutput")
    nested_used = nested_tree.nodes.new("GeometryNodeCollectionInfo")
    nested_used.inputs["Collection"].default_value = nested_used_group
    nested_unused = nested_tree.nodes.new("GeometryNodeCollectionInfo")
    nested_unused.inputs["Collection"].default_value = unused_group
    nested_tree.links.new(
        nested_used.outputs["Instances"], nested_output.inputs["Used"]
    )
    nested_tree.links.new(
        nested_unused.outputs["Instances"], nested_output.inputs["Unused"]
    )
    nested_node = tree.nodes.new("GeometryNodeGroup")
    nested_node.node_tree = nested_tree
    tree.links.new(nested_node.outputs["Used"], join.inputs["Geometry"])
    tree.links.new(join.outputs["Geometry"], output.inputs["Geometry"])
    unused = tree.nodes.new("GeometryNodeCollectionInfo")
    unused.inputs["Collection"].default_value = unused_group
    modifier = host.modifiers.new("CMask Geometry Nodes", "NODES")
    modifier.node_group = tree

    dependencies, unresolved = geometry_node_dependencies(host)
    assert source in dependencies and nested_used_source in dependencies
    assert unused_source not in dependencies
    assert len(unresolved) == 1
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    issues, resolution = validate_groups(settings)
    assert source in resolution.geometry_node_sources[host]
    issue = next(item for item in issues
                 if item.code == "GEOMETRY_NODES_SOURCE_GROUP")
    assert issue.subject == host.name and "CM_GeometrySource" in issue.message
    dynamic_issue = next(item for item in issues
                         if item.code == "GEOMETRY_NODES_DYNAMIC_SOURCE")
    assert dynamic_issue.subject == host.name
    settings.geometry_nodes_split_sources = True
    issues, _resolution = validate_groups(settings)
    assert any(item.code == "GEOMETRY_NODES_SPLIT_HOST_ROLE" and
               item.level == "ERROR" for item in issues)
    host_item = next(item for item in settings.groups
                     if item.collection == host_group)
    host_item.enabled = False
    assert bpy.ops.cmask.configure_geometry_nodes_split() == {"FINISHED"}
    assert host_item.role == "IGNORE" and settings.geometry_nodes_split_sources
    assert host_item.enabled
    issues, _resolution = validate_groups(settings)
    assert not any(item.code in {
        "GEOMETRY_NODES_SPLIT_HOST_ROLE", "GEOMETRY_NODES_SOURCE_GROUP",
    } for item in issues)


def test_batch_paths_disambiguate_sanitized_names():
    import tempfile
    from collection_mask_exporter.core.output_manager import unique_mask_paths
    scene = reset_scene()
    first = bpy.data.collections.new("CM_A:B")
    second = bpy.data.collections.new("CM_A?B")
    scene.collection.children.link(first)
    scene.collection.children.link(second)
    settings = scene.cmask_settings
    settings.output_directory = tempfile.mkdtemp(prefix="cmask-path-test-")
    bpy.ops.cmask.scan()
    paths = [path for _item, path in unique_mask_paths(scene, settings, settings.groups)]
    assert len(paths) == len(set(path.lower() for path in paths)) == 2


def test_restore_survives_deleted_datablocks():
    from collection_mask_exporter.core.state_manager import (
        capture_scene_state, restore_scene_state,
    )
    scene = reset_scene()
    survivor = add_mesh(scene.collection, "Survivor")
    victim = add_mesh(scene.collection, "Victim")
    victim_mesh = victim.data
    survivor.color = (0.1, 0.2, 0.3, 1.0)
    state = capture_scene_state(bpy.context)
    survivor.color = (1.0, 1.0, 1.0, 1.0)
    bpy.data.objects.remove(victim, do_unlink=True)
    bpy.data.meshes.remove(victim_mesh)
    errors = restore_scene_state(bpy.context, state)
    assert tuple(round(value, 3) for value in survivor.color) == (0.1, 0.2, 0.3, 1.0)
    assert errors


def test_manual_groups_and_priority_controls():
    scene = reset_scene()
    first = bpy.data.collections.new("ManualFirst")
    second = bpy.data.collections.new("ManualSecond")
    scene.collection.children.link(first)
    scene.collection.children.link(second)
    settings = scene.cmask_settings
    settings.scan_mode = "MANUAL"
    settings.manual_collection = first
    assert bpy.ops.cmask.add_manual_group() == {"FINISHED"}
    settings.manual_collection = second
    assert bpy.ops.cmask.add_manual_group() == {"FINISHED"}
    assert [item.collection for item in settings.groups] == [first, second]
    settings.active_group_index = 1
    assert bpy.ops.cmask.move_group(direction="UP") == {"FINISHED"}
    assert [item.collection for item in settings.groups] == [second, first]
    assert second["cmask_priority"] == 0 and first["cmask_priority"] == 1
    bpy.ops.cmask.scan()
    assert [item.collection for item in settings.groups] == [second, first]
    assert bpy.ops.cmask.remove_group() == {"FINISHED"}
    assert len(settings.groups) == 1


def test_templates_reserved_names_and_issue_details():
    import tempfile
    from collection_mask_exporter.core.output_manager import (
        OutputTemplateError, mask_path, safe_filename,
    )
    scene = reset_scene()
    empty = bpy.data.collections.new("CM_Empty")
    scene.collection.children.link(empty)
    settings = scene.cmask_settings
    settings.output_directory = tempfile.mkdtemp(prefix="cmask-template-test-")
    settings.filename_template = "{scene}_{collection}_{frame}_{mode}"
    bpy.ops.cmask.scan()
    path = mask_path(scene, settings, "Part")
    assert "Scene_Part_0001_visible.png" in path
    assert safe_filename("NUL") == "_NUL"
    settings.filename_template = "{unknown}"
    try:
        mask_path(scene, settings, "Part")
        raise AssertionError("Invalid template did not fail")
    except OutputTemplateError:
        pass
    settings.filename_template = "{blend}_{collection}_{mode}"
    bpy.ops.cmask.validate()
    assert len(settings.issues) == 1
    assert settings.issues[0].code == "EMPTY"


def test_alpha_morphology():
    from collection_mask_exporter.core.postprocess import morph_alpha
    single = [0.0] * 25
    single[12] = 1.0
    expanded = morph_alpha(single, 5, 5, 1)
    assert sum(value > 0.99 for value in expanded) == 9
    block = [0.0] * 25
    for y in range(1, 4):
        for x in range(1, 4):
            block[y * 5 + x] = 1.0
    contracted = morph_alpha(block, 5, 5, -1)
    assert sum(value > 0.99 for value in contracted) == 1


def test_collection_cryptomatte_writer():
    import json
    import os
    import struct
    import tempfile
    import OpenImageIO as oiio
    import numpy
    from collection_mask_exporter.core.cryptomatte import (
        combine_collection_cryptomatte, cryptomatte_hash,
    )

    official_vectors = {
        "hello": 6.07056271024e-17,
        "cube": -4.08461912519e15,
        "sphere": 2.79018604383e15,
        "plane": 3.66557617593e-11,
        "равнина": -1.31926312124e-25,
        "mädchen": 6.23612982116e25,
    }
    for name, expected in official_vectors.items():
        expected = struct.unpack("<f", struct.pack("<f", expected))[0]
        assert cryptomatte_hash(name)[1] == expected

    with tempfile.TemporaryDirectory(prefix="cmask-crypto-test-") as temp:
        paths = []
        for name, alpha in (("CM_First", (0.75, 0.20)),
                            ("CM_Second", (0.25, 0.80))):
            path = os.path.join(temp, name + ".exr")
            spec = oiio.ImageSpec(2, 1, 4, oiio.FLOAT)
            spec.channelnames = ["R", "G", "B", "A"]
            pixels = numpy.zeros((1, 2, 4), dtype=numpy.float32)
            pixels[0, :, 3] = alpha
            output = oiio.ImageOutput.create(path)
            assert output and output.open(path, spec)
            assert output.write_image(pixels)
            assert output.close()
            paths.append((name, path))

        final_path = os.path.join(temp, "collections.exr")
        manifest = combine_collection_cryptomatte(final_path, paths, depth=2)
        image_input = oiio.ImageInput.open(final_path)
        assert image_input
        try:
            spec = image_input.spec()
            assert list(spec.channelnames) == [
                "CryptoCollection00.R", "CryptoCollection00.G",
                "CryptoCollection00.B", "CryptoCollection00.A",
            ]
            metadata_id = cryptomatte_hash("CryptoCollection")[2][:-1]
            prefix = f"cryptomatte/{metadata_id}/"
            assert spec.get_string_attribute(prefix + "name") == "CryptoCollection"
            embedded = json.loads(spec.get_string_attribute(prefix + "manifest"))
            assert embedded == manifest
            pixels = image_input.read_image(oiio.FLOAT)
        finally:
            image_input.close()

        first_id = cryptomatte_hash("CM_First")[1]
        second_id = cryptomatte_hash("CM_Second")[1]
        assert pixels[0, 0, 0] == first_id
        assert pixels[0, 0, 2] == second_id
        assert tuple(round(float(value), 2) for value in pixels[0, 0, (1, 3)]) == (0.75, 0.25)
        assert pixels[0, 1, 0] == second_id
        assert pixels[0, 1, 2] == first_id
        assert tuple(round(float(value), 2) for value in pixels[0, 1, (1, 3)]) == (0.80, 0.20)


def test_cli_job_resolution():
    import json
    import os
    import tempfile
    from collection_mask_exporter.cli import resolve_config

    with tempfile.TemporaryDirectory(prefix="cmask-cli-config-") as temp:
        path = os.path.join(temp, "job.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({
                "operation": "batch",
                "output_directory": "from-job",
                "frame_mode": "RANGE",
                "frame_start": 2,
                "frame_end": 8,
                "frame_step": 2,
                "write_report": True,
                "geometry_nodes_split_sources": True,
                "dynamic_geometry_enabled": True,
                "dynamic_attribute_name": "delivery_id",
            }, handle)
        config = resolve_config([
            "--job", path, "--operation", "cryptomatte",
            "--output", "from-cli", "--no-report",
            "--cryptomatte-depth", "10",
        ])
        assert config["operation"] == "cryptomatte"
        assert config["output_directory"] == "from-cli"
        assert config["cryptomatte_depth"] == "10"
        assert config["frame_start"] == 2 and config["frame_step"] == 2
        assert config["write_report"] is False
        assert config["geometry_nodes_split_sources"] is True
        assert config["dynamic_geometry_enabled"] is True
        assert config["dynamic_attribute_name"] == "delivery_id"


def test_incremental_sync_preserves_rows_and_selection():
    scene = reset_scene()
    first = bpy.data.collections.new("CM_First")
    second = bpy.data.collections.new("CM_Second")
    scene.collection.children.link(first)
    scene.collection.children.link(second)
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    settings.active_group_index = 1
    settings.groups[1]["incremental_test"] = "kept"

    third = bpy.data.collections.new("CM_Third")
    scene.collection.children.link(third)
    bpy.ops.cmask.scan()
    second_index = next(
        i for i, item in enumerate(settings.groups) if item.collection == second
    )
    assert settings.groups[second_index].get("incremental_test") == "kept"
    assert settings.active_group_index == second_index

    bpy.data.collections.remove(first)
    bpy.ops.cmask.scan()
    assert [item.collection for item in settings.groups] == [second, third]
    assert settings.groups[0].get("incremental_test") == "kept"
    assert settings.active_group_index == 0


def test_scene_presets_round_trip():
    scene = reset_scene()
    first = bpy.data.collections.new("CM_First")
    second = bpy.data.collections.new("CM_Second")
    scene.collection.children.link(first)
    scene.collection.children.link(second)
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    settings.preset_name = "交付设置"
    settings.output_format = "OPEN_EXR"
    settings.color_depth = "32"
    settings.edge_adjustment = 3
    settings.alpha_mode = "PREMULTIPLIED"
    settings.transparent_material_mode = "EXCLUDE"
    settings.photoshop_create_channels = False
    settings.geometry_nodes_split_sources = True
    settings.dynamic_geometry_enabled = True
    settings.dynamic_attribute_name = "delivery_mask_id"
    settings.scan_visible_only = True
    settings.cryptomatte_depth = "10"
    settings.camera_mode = "ALL"
    settings.frame_mode = "RANGE"
    settings.groups[0].role = "HOLDOUT"
    settings.groups[0].dynamic_id = 17
    settings.groups[1].color = (0.2, 0.3, 0.4, 1.0)
    assert bpy.ops.cmask.save_preset() == {"FINISHED"}

    settings.output_format = "PNG"
    settings.color_depth = "8"
    settings.edge_adjustment = 0
    settings.alpha_mode = "STRAIGHT"
    settings.transparent_material_mode = "INCLUDE"
    settings.photoshop_create_channels = True
    settings.geometry_nodes_split_sources = False
    settings.dynamic_geometry_enabled = False
    settings.dynamic_attribute_name = "changed"
    settings.scan_visible_only = False
    settings.cryptomatte_depth = "6"
    settings.camera_mode = "CURRENT"
    settings.frame_mode = "CURRENT"
    settings.groups[0].role = "MASK"
    settings.groups[1].color = (1.0, 0.0, 0.0, 1.0)
    # Simulate importing the preset configuration into a scene where the
    # Collection kept its name but received a different UUID.
    second["cmask_uuid"] = "replacement-uuid"
    assert bpy.ops.cmask.apply_preset() == {"FINISHED"}
    assert settings.output_format == "OPEN_EXR"
    assert settings.color_depth == "32" and settings.edge_adjustment == 3
    assert settings.alpha_mode == "PREMULTIPLIED"
    assert settings.transparent_material_mode == "EXCLUDE"
    assert settings.photoshop_create_channels is False
    assert settings.geometry_nodes_split_sources is True
    assert settings.dynamic_geometry_enabled is True
    assert settings.dynamic_attribute_name == "delivery_mask_id"
    assert settings.scan_visible_only is True
    assert settings.cryptomatte_depth == "10"
    assert settings.camera_mode == "ALL" and settings.frame_mode == "RANGE"
    assert settings.groups[0].role == "HOLDOUT"
    assert settings.groups[0].dynamic_id == 17
    assert tuple(round(v, 2) for v in settings.groups[1].color) == (0.2, 0.3, 0.4, 1.0)
    assert bpy.ops.cmask.delete_preset() == {"FINISHED"}
    assert len(settings.presets) == 0


def test_outliner_manual_add_operator():
    scene = reset_scene()
    scanned = bpy.data.collections.new("CM_Scanned")
    added = bpy.data.collections.new("FromOutliner")
    scene.collection.children.link(scanned)
    scene.collection.children.link(added)
    settings = scene.cmask_settings
    bpy.ops.cmask.scan()
    result = bpy.ops.cmask.add_outliner_collection(collection_name=added.name)
    assert result == {"FINISHED"}
    assert settings.scan_mode == "MANUAL"
    assert [item.collection for item in settings.groups] == [scanned, added]
    assert settings.active_group_index == 1


def test_transparent_material_detection():
    from collection_mask_exporter.core.material_override import ensure_material_node_tree
    from collection_mask_exporter.core.transparency import (
        material_uses_transparency, object_uses_transparency,
    )
    scene = reset_scene()
    obj = add_mesh(scene.collection, "TransparentCandidate")
    material = bpy.data.materials.new("AlphaMaterial")
    obj.data.materials.append(material)
    assert not material_uses_transparency(material)
    material.diffuse_color = (1.0, 1.0, 1.0, 0.5)
    assert material_uses_transparency(material)
    assert object_uses_transparency(obj)
    material.diffuse_color = (1.0, 1.0, 1.0, 1.0)
    ensure_material_node_tree(material)
    principled = next(
        node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"
    )
    principled.inputs["Alpha"].default_value = 0.25
    assert material_uses_transparency(material)

    source = bpy.data.collections.new("TransparentInstanceSource")
    source.objects.link(obj)
    scene.collection.objects.unlink(obj)
    host = bpy.data.objects.new("TransparentInstance", None)
    host.instance_type = "COLLECTION"
    host.instance_collection = source
    scene.collection.objects.link(host)
    assert object_uses_transparency(host)


def test_photoshop_handoff_generator():
    import json
    import tempfile
    from pathlib import Path
    from collection_mask_exporter.core.photoshop import (
        build_photoshop_jsx, write_photoshop_handoff,
    )

    scene = reset_scene()
    settings = scene.cmask_settings
    with tempfile.TemporaryDirectory(prefix="cmask-photoshop-test-") as temp:
        root = Path(temp)
        color_dir = root / "Color_ID"
        mask_dir = root / "Masks"
        color_dir.mkdir()
        mask_dir.mkdir()
        color = color_dir / "彩色 ID.png"
        mask = mask_dir / "主体蒙版.png"
        color.write_bytes(b"test")
        mask.write_bytes(b"test")
        settings.output_directory = str(root)
        for path in (color, mask):
            item = settings.last_outputs.add()
            item.path = str(path)

        script = build_photoshop_jsx([str(color), str(mask)], str(root / "交付.psd"))
        assert "PhotoshopSaveOptions" in script
        assert "createAlphaChannel" in script and "SelectionType.REPLACE" in script
        assert "options.alphaChannels = true" in script
        assert "app.displayDialogs" not in script
        assert "stringIDToTypeID(\"transparencyEnum\")" in script
        assert "channelErrors.push" in script
        assert "activeLayerIsEmpty" in script and "emptyAlpha" in script
        assert "Color ID - " in script and "Mask - " in script
        assert "\\u5f69\\u8272" in script and "\\u4e3b\\u4f53" in script

        jsx_path, manifest_path, psd_path = write_photoshop_handoff(scene, settings)
        assert Path(jsx_path).is_file() and Path(manifest_path).is_file()
        assert Path(jsx_path).read_bytes().startswith(b"\xef\xbb\xbf")
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        assert manifest["schema"] == "cmask.photoshop_handoff.v1"
        assert manifest["create_alpha_channels"] is True
        assert len(manifest["outputs"]) == 2
        assert manifest["outputs"][1]["layer"].startswith("Mask - ")
        assert manifest["outputs"][0]["channel"] is None
        assert manifest["outputs"][1]["channel"].startswith("CMask - ")
        assert psd_path.endswith("_cmask_photoshop.psd")

        settings.photoshop_create_channels = False
        jsx_path, manifest_path, _psd_path = write_photoshop_handoff(scene, settings)
        generated = Path(jsx_path).read_text(encoding="utf-8-sig")
        assert "var cmaskCreateChannels = false;" in generated
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        assert manifest["create_alpha_channels"] is False
        assert all(item["channel"] is None for item in manifest["outputs"])


def test_compatibility_diagnostic():
    import json
    import tempfile
    from pathlib import Path
    from collection_mask_exporter.core.compatibility import (
        blender_support_status, collect_compatibility, write_compatibility_report,
    )

    scene = reset_scene()
    settings = scene.cmask_settings
    settings.output_directory = tempfile.mkdtemp(prefix="cmask-compatibility-test-")
    payload = collect_compatibility(scene)
    assert blender_support_status((4, 4, 9)) == "UNSUPPORTED"
    assert blender_support_status((4, 5, 0)) == "SUPPORTED"
    assert blender_support_status((5, 0, 99)) == "SUPPORTED"
    assert blender_support_status((5, 1, 0)) == "UNVALIDATED"
    assert blender_support_status((5, 2, 0)) == "SUPPORTED"
    assert blender_support_status((5, 3, 0)) == "UNVALIDATED"
    assert blender_support_status((6, 0, 0)) == "FUTURE_UNVALIDATED"
    assert payload["schema"] == "cmask.compatibility.v1"
    assert payload["compatible"] is True
    assert not payload["required_failures"]
    assert {item["key"] for item in payload["checks"]} >= {
        "view_layer_create_remove", "view_layer_material_override",
        "layer_collection_flags", "material_node_tree", "openimageio",
    }
    path, written = write_compatibility_report(scene, settings)
    assert Path(path).is_file() and written["addon_version"] == "0.7.0"
    with open(path, "r", encoding="utf-8") as handle:
        assert json.load(handle)["blender_version"] == bpy.app.version_string
    assert bpy.ops.cmask.compatibility_report() == {"FINISHED"}
    assert settings.last_diagnostic_report == path
    assert settings.last_status


for test in (test_scan_and_stable_color, test_nested_explicit_child_wins,
             test_multiple_membership_conflict,
             test_scan_preserves_role_and_enabled_state,
             test_scan_current_view_layer_visibility,
             test_explicit_grandchild_wins_through_implicit_parent,
             test_nested_collection_instance_is_renderable_host,
             test_collection_instance_source_group_conflict,
             test_geometry_nodes_source_resolution,
             test_batch_paths_disambiguate_sanitized_names,
             test_restore_survives_deleted_datablocks,
             test_manual_groups_and_priority_controls,
             test_templates_reserved_names_and_issue_details,
             test_alpha_morphology,
             test_collection_cryptomatte_writer,
             test_cli_job_resolution,
             test_incremental_sync_preserves_rows_and_selection,
             test_scene_presets_round_trip,
             test_outliner_manual_add_operator,
             test_transparent_material_detection,
             test_photoshop_handoff_generator,
             test_compatibility_diagnostic):
    test()
    print("PASS", test.__name__)

print("CMASK CORE TESTS PASSED")
addon.unregister()
