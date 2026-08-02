# CMask Geometry Nodes 静态源拆分

CMask v0.6.0 可以在不修改节点树的前提下，把同一个 Geometry Nodes 宿主中
直接引用的静态 Collection/Object 源拆成多个 CMask 组。

## 支持条件

- Geometry Nodes 使用直接设置的 `Collection Info` 或 `Object Info`。
- 源对象位于已经加入 CMask 的显式 MASK Collection。
- Geometry Nodes 宿主位于单独的 CMask Collection，角色设置为 IGNORE。
- 启用“拆分 Geometry Nodes 静态源”。
- 当前 Blender 包含 OpenImageIO；可用“API 兼容性诊断”检查。

扫描完成后可直接点击“一键配置 GN 静态源拆分”。插件会识别包含显式静态源
的宿主、重新启用被禁用的宿主组、将其设置为 IGNORE，并启用拆分选项；源组
角色仍由用户决定，需要拆分输出的源应保持为 MASK。随后执行“检查场景”确认
配置。未连接到节点组输出的 Collection/Object Info 不参与识别；嵌套节点组
也只分析外层实际使用的输出插口。

宿主使用 IGNORE 是为了说明它只负责生成几何，不占用独立 ID。导出某个源组
时，CMask 临时保持宿主可见，同时使用源对象的 Hide Render/Holdout 状态分离
节点内部几何；操作完成后全部恢复。

## 推荐结构

```text
Scene Collection
├─ CM_GN_Host              # IGNORE，包含 Geometry Nodes 宿主
└─ GN_Source               # 可在 View Layer 中排除
   ├─ CM_Part_A            # MASK
   └─ CM_Part_B            # MASK
```

Geometry Nodes 的 Collection Info 直接指向 `GN_Source`。如果源根集合在活动
View Layer 中排除，应关闭“仅扫描当前 View Layer 可见集合”，或者使用手动模式
添加 `CM_Part_A` 和 `CM_Part_B`。

## 输出行为

- 独立蒙版：每个源 MASK 正常支持 VISIBLE 和 SILHOUETTE。
- 彩色 ID：先渲染各组 VISIBLE 覆盖率，再按组颜色合成 Straight Alpha 文件。
- Multilayer EXR：每个源 MASK 对应独立 RGBA 层。
- Cryptomatte：每个源 MASK 对应独立名称和 ID。
- JSON 报告记录 `geometry_nodes_split_sources=true`。
- 宿主未设为 IGNORE 时，场景检查报告 `GEOMETRY_NODES_SPLIT_HOST_ROLE` 错误；
  没有可用 MASK 源时报告 `GEOMETRY_NODES_SPLIT_NO_MASK` 警告。

拆分不会应用边缘扩张到彩色 ID 的内部合成过程；独立蒙版仍使用用户设置。

## 当前边界

- 动态连接的 Collection/Object socket 无法由静态模式确定，场景检查会给出
  `GEOMETRY_NODES_DYNAMIC_SOURCE`。
- Simulation Zone、Repeat Zone、驱动或字段计算出的逐实例语义请使用 v0.6.0
  的求值后 `cmask_id` 协议，见 `CMask_Geometry_Nodes_动态字段.md`。
- 一个透明源会触发当前对象级透明材质保守策略，可能排除整个宿主。
- 拆分彩色 ID 暂不支持 Render Result 预览，请导出 PNG/EXR 检查。
