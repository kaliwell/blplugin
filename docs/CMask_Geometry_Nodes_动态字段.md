# CMask Geometry Nodes 动态字段 / Dynamic Fields

CMask v0.6.0 为 Blender 5.0+ 提供求值后动态几何拆分。它不猜测节点树中字段、
驱动、Simulation Zone 或 Repeat Zone 的意图，而是在每次渲染时读取最终网格上的
显式整数属性。这使逐帧和逐实例变化具有确定、可验证的交付语义。

CMask v0.6.0 supports evaluated dynamic geometry splitting on Blender 5.0+.
Instead of guessing the intent of fields, drivers, Simulation Zones, or Repeat
Zones, it reads an explicit integer attribute from the final evaluated mesh on
every render.

## 配置 / Setup

1. 为每个需要输出的 Collection 建立 CMask 组，并设置唯一的“动态 GN ID”。
2. 把 Geometry Nodes 宿主放入一个单独 CMask Collection，并将角色设为 IGNORE。
3. 在节点树中把组 ID 写入名为 `cmask_id` 的整数属性。
4. 在输出前使用 `Store Named Attribute`，域选择 Face，数据类型选择 Integer。
5. 如果节点树生成实例，先用 `Realize Instances`，再确保 `cmask_id` 存在于 Face 域。
6. 在面板启用“动态 GN 属性”，属性名保持 `cmask_id`，然后执行“检查场景”。

1. Give each output Collection a unique **Dynamic GN ID**.
2. Put the Geometry Nodes host in a separate CMask Collection with role **Ignore**.
3. Write the group ID to an integer attribute named `cmask_id`.
4. Before output, use **Store Named Attribute**, Face domain, Integer type.
5. For instances, use **Realize Instances** and ensure `cmask_id` reaches Face domain.
6. Enable **Dynamic GN Attribute**, keep the attribute name as `cmask_id`, and run
   **Check Scene**.

## 动态行为 / Dynamic behavior

- 驱动和逐帧字段会在每次单帧或批量渲染时重新求值。
- Simulation Zone 与 Repeat Zone 受支持的条件是最终输出网格保留 FACE/INT 属性。
- 一个宿主可以输出多个 ID；每个 ID 会形成独立 Color ID、Mask、Multilayer EXR
  和 Cryptomatte 语义。
- 原宿主、节点树和正式材质不会被修改；临时对象、网格与 Collection 在成功或失败后清理。

- Drivers and per-frame fields are evaluated again for every single or batch render.
- Simulation and Repeat Zones work when the final mesh retains the FACE/INT attribute.
- One host may emit multiple IDs, each becoming an independent Color ID, mask,
  Multilayer EXR layer, and Cryptomatte identity.
- The original host, node tree, and production materials are untouched. Temporary
  objects, meshes, and Collections are cleaned after success or failure.

## 边界 / Limits

- 当前协议只读取求值后 Mesh 的 FACE 域 INT 属性，不直接解释节点或 INSTANCE 域。
- `0` 或负值不映射到任何输出组；未配置的正值会被忽略。
- 每个正整数 ID 只能分配给一个启用组。
- Blender 4.5 继续支持既有静态 GN 源拆分，但不支持本动态协议。
- Blender 6.0 正式版尚不可获得，因此当前没有 6.0 正式版实机认证；发布后需重跑完整矩阵。

- The protocol currently reads only a FACE-domain INT attribute on an evaluated Mesh;
  it does not interpret nodes or the INSTANCE domain directly.
- Zero and negative values are unmapped; unconfigured positive values are ignored.
- Each positive ID can belong to only one enabled group.
- Blender 4.5 retains static GN source splitting but not this dynamic protocol.
- A Blender 6.0 stable build is not yet available, so formal 6.0 hardware validation
  remains pending until release.
