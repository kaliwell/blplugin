from .instances import collection_source_objects


def geometry_nodes_modifiers(obj):
    return [
        modifier for modifier in getattr(obj, "modifiers", ())
        if modifier.type == "NODES" and getattr(modifier, "node_group", None)
    ]


def is_geometry_nodes_object(obj):
    return bool(geometry_nodes_modifiers(obj))


def _data_input(node, socket_type, fallback_name):
    for socket in node.inputs:
        if (getattr(socket, "bl_socket_idname", "") == socket_type or
                getattr(socket, "type", "") == socket_type.replace("NodeSocket", "").upper()):
            return socket
    return node.inputs.get(fallback_name)


def _socket_keys(socket):
    return {
        value for value in (
            getattr(socket, "identifier", ""), getattr(socket, "name", ""),
        ) if value
    }


def _is_geometry_socket(socket):
    return (
        getattr(socket, "bl_socket_idname", "") == "NodeSocketGeometry" or
        getattr(socket, "type", "") == "GEOMETRY"
    )


def _output_reachable_nodes(tree, requested_outputs=None):
    """Return reachable nodes and outputs used on nested group nodes.

    Geometry node trees often keep disabled experiments or helper nodes around.
    Treating every node in the datablock as an evaluated dependency can make a
    disconnected Collection Info node change CMask ownership unexpectedly. For
    nested groups, only the outer node's connected output sockets are traced.
    """
    outputs = [
        node for node in tree.nodes
        if getattr(node, "bl_idname", "") == "NodeGroupOutput"
    ]
    active = [node for node in outputs if getattr(node, "is_active_output", False)]
    outputs = active or outputs
    requested = set(requested_outputs or ())
    selected_inputs = set()
    for output in outputs:
        for socket in output.inputs:
            if ((requested and _socket_keys(socket) & requested) or
                    (not requested and _is_geometry_socket(socket))):
                selected_inputs.add(socket)
    if not selected_inputs:
        selected_inputs = {
            socket for output in outputs for socket in output.inputs
            if getattr(socket, "is_linked", False)
        }

    links_by_target = {}
    for link in tree.links:
        links_by_target.setdefault(link.to_node, []).append(link)
    reachable = set()
    pending = []
    nested_outputs = {}

    def add_link(link):
        upstream = link.from_node
        nested = getattr(upstream, "node_tree", None)
        if nested is not None:
            nested_outputs.setdefault(upstream, set()).update(
                _socket_keys(link.from_socket)
            )
        if upstream not in reachable:
            reachable.add(upstream)
            pending.append(upstream)

    for output in outputs:
        for link in links_by_target.get(output, ()):
            if link.to_socket in selected_inputs:
                add_link(link)
    while pending:
        node = pending.pop()
        for link in links_by_target.get(node, ()):
            add_link(link)
    return reachable, nested_outputs


def geometry_node_dependencies(obj):
    """Resolve direct Collection/Object Info dependencies from Geometry Nodes.

    Linked Collection/Object sockets are intentionally reported as unresolved:
    their value can vary per modifier or evaluation context and guessing would
    make a mask silently incomplete.
    """
    dependencies = set()
    unresolved = []
    visited = set()

    def walk(tree, requested_outputs=None):
        visit_key = (tree, frozenset(requested_outputs or ()))
        if tree is None or visit_key in visited:
            return
        visited.add(visit_key)
        reachable, nested_outputs = _output_reachable_nodes(
            tree, requested_outputs
        )
        for node in reachable:
            node_id = getattr(node, "bl_idname", "")
            if node_id == "GeometryNodeCollectionInfo":
                socket = _data_input(node, "NodeSocketCollection", "Collection")
                if socket is None or socket.is_linked:
                    unresolved.append(f"{tree.name}/{node.name}: Collection")
                elif socket.default_value is not None:
                    dependencies.update(collection_source_objects(socket.default_value))
            elif node_id == "GeometryNodeObjectInfo":
                socket = _data_input(node, "NodeSocketObject", "Object")
                if socket is None or socket.is_linked:
                    unresolved.append(f"{tree.name}/{node.name}: Object")
                elif socket.default_value is not None:
                    dependencies.add(socket.default_value)
            nested = getattr(node, "node_tree", None)
            if nested is not None:
                walk(nested, nested_outputs.get(node))

    for modifier in geometry_nodes_modifiers(obj):
        walk(modifier.node_group)
    # Collection Info may itself contain Geometry Nodes hosts. Preserve their
    # static dependencies as well, with both object and node-tree cycle guards.
    processed_objects = {obj}
    pending = list(dependencies)
    while pending:
        dependency = pending.pop()
        if dependency in processed_objects:
            continue
        processed_objects.add(dependency)
        before = set(dependencies)
        for modifier in geometry_nodes_modifiers(dependency):
            walk(modifier.node_group)
        pending.extend(dependencies - before - processed_objects)
    dependencies.discard(obj)
    return dependencies, unresolved
