# Blender Collection Mask Exporter 插件开发方案

> 暂定名称：**Collection Mask Exporter**
> 中文名称：**集合蒙版导出器**
> 插件简称：**CMask**
> 文档版本：v0.3
> 当前目标版本：Blender 4.5 LTS、5.0、5.2

> 实现状态（2026-08-01）：核心导出、边缘调整、PNG/OpenEXR、命名模板、
> JSON 报告、多相机/帧范围、场景预设、Outliner 入口、增量同步、可见
> View Layer 扫描过滤、Alpha
> 预乘模式、透明材质对象级策略、Compositor 图像节点生成、Multilayer
> EXR 独立 RGBA 层、Collection Cryptomatte、后台命令行任务和 Collection
> Instance 深层依赖解析已经落地。
> 尚未完成的路线项目见第 28 节。

---

## 1. 项目背景

在产品渲染、电商视觉、室内效果图和广告静帧工作流中，用户通常已经通过 Blender 大纲视图中的 `Collection` 完成了结构分组，例如：

```text
Scene Collection
├─ CM_外壳
├─ CM_屏幕
├─ CM_按键
├─ CM_金属
├─ CM_Logo
├─ CM_前景遮挡
└─ 灯光与辅助对象
```

但 Blender 原生的 Object Index、Material Index 和 Cryptomatte 主要以“物体”或“材质”为单位，不能直接把用户已经整理好的 Collection 自动转换为 Photoshop 友好的分组蒙版。

本插件用于打通以下流程：

```text
Outliner Collection 分组
        ↓
自动识别和同步蒙版组
        ↓
每组分配稳定颜色
        ↓
生成彩色 Collection ID 图
        ↓
批量生成每组独立透明蒙版
        ↓
在 Photoshop 中按组调色与合成
```

---

## 2. 产品定位

### 2.1 核心定位

将 Blender 的 Collection 结构直接转换为 Photoshop、Affinity Photo、Nuke、Fusion 等软件可使用的蒙版资源。

### 2.2 主要用户

- 电商产品渲染师
- 产品广告设计师
- 建筑与室内可视化人员
- Blender + Photoshop 后期用户
- 需要按模型模块批量调色的独立设计师

### 2.3 核心价值

1. 不再逐个选择几十个物体创建蒙版。
2. Collection 中新增、删除或移动物体后可重新同步。
3. 不破坏正式材质和正式渲染设置。
4. 同时提供彩色 ID 图与精确透明 PNG 蒙版。
5. 正确处理前后遮挡、Holdout 和透明背景。
6. 输出命名与 Collection 名称自动对应。

---

## 3. MVP 功能范围

首个可用版本建议控制在以下六项核心功能内：

1. 扫描并管理 Collection 蒙版组。
2. 为每个 Collection 分配稳定唯一颜色。
3. 输出一张彩色 Collection ID 图。
4. 批量输出每个 Collection 的独立 RGBA 蒙版。
5. 支持遮挡组和透明阻隔。
6. 导出后完整恢复用户场景状态。

第一版不追求 PSD、多层 EXR、Geometry Nodes 实例拆分等高级功能，优先保证结果正确和流程稳定。

---

## 4. Collection 角色模型

每个被插件识别的 Collection 可设置一种角色。

| 角色 | 说明 | 是否输出独立蒙版 | 是否参与遮挡 |
|---|---|---:|---:|
| `MASK` | 正常蒙版组，分配颜色并导出 | 是 | 是 |
| `HOLDOUT` | 只用于阻隔，在结果中切出透明区域 | 否 | 是 |
| `IGNORE` | 完全忽略，不参与蒙版计算 | 否 | 否 |
| `OCCLUDER` | 只遮挡其他组，但不单独导出 | 否 | 是 |

### 4.1 为什么需要区分 HOLDOUT 与 OCCLUDER

- `HOLDOUT`：该区域最终必须是透明洞。
- `OCCLUDER`：仅用于保持真实可见关系，例如前景物体遮住后方产品，但前景物体本身不需要输出蒙版。

该设计可以避免把所有非目标组简单 Exclude 后造成“后方物体完整穿透显示”的错误。

---

## 5. 蒙版输出模式

独立蒙版必须支持两种模式，这是插件是否真正实用的关键。

### 5.1 可见区域模式 `VISIBLE`

只输出当前相机中真实可见的目标区域。

处理逻辑：

```text
目标 Collection         → 白色蒙版
其他 MASK Collection    → Holdout，保留真实遮挡关系
OCCLUDER Collection     → Holdout
HOLDOUT Collection      → Holdout
IGNORE Collection       → Exclude
背景                    → 透明
```

适合：

- Photoshop 局部调色
- 产品渲染后期
- 只修改当前画面中实际可见的区域

### 5.2 完整轮廓模式 `SILHOUETTE`

输出目标 Collection 的完整投影视图，不考虑其他组对它的遮挡。

处理逻辑：

```text
目标 Collection         → 白色蒙版
其他所有 Collection     → Exclude
背景                    → 透明
```

适合：

- 完整轮廓选区
- 后续二维排版
- 对象整体外形分析
- 特殊合成需求

默认使用 `VISIBLE`，因为它更符合产品渲染和 Photoshop 调色需求。

---

## 6. Collection 扫描方式

提供三种扫描方式：

### 6.1 名称前缀扫描

默认识别以指定前缀开头的 Collection：

```text
CM_外壳
CM_屏幕
CM_按键
```

默认前缀：

```text
CM_
```

优点是不会误识别灯光、相机、参考对象和辅助集合。

### 6.2 顶级 Collection 扫描

识别 Scene Collection 下第一层 Collection。

适用于已经严格按顶层模块整理的场景。

### 6.3 手动选择

用户在插件列表中手动添加 Collection。

适合结构复杂或不能修改命名的旧项目。

---

## 7. 嵌套 Collection 规则

### 7.1 默认递归

启用“包括子集合”后，父级蒙版组自动包含全部子集合对象：

```text
CM_外壳
├─ 上盖
├─ 下盖
└─ 装饰件
```

以上对象统一归入 `CM_外壳`。

### 7.2 子级显式蒙版优先

如果子集合本身也被设置为 `MASK`：

```text
CM_外壳
└─ CM_金属装饰
```

处理规则：

```text
CM_金属装饰中的对象 → 归属 CM_金属装饰
其余对象             → 归属 CM_外壳
```

即“显式子组优先于父组继承”，避免一个对象重复进入两个蒙版。

---

## 8. 多重归属冲突

Blender 允许同一对象链接到多个 Collection，因此插件必须进行冲突检测。

### 8.1 默认策略：优先级解析

插件列表中位置越高，优先级越高。

```text
1. CM_Logo
2. CM_外壳
```

如果 `Logo_Object` 同时存在于两个集合，最终归入 `CM_Logo`。

### 8.2 严格模式

开启严格模式后，只要发现对象属于多个启用的蒙版组，就中止导出并显示报告：

```text
对象：Logo_Object
重复归属：
- CM_Logo
- CM_外壳
```

### 8.3 冲突报告

插件应提供“检查场景”按钮，输出以下问题：

- 对象重复归属
- 空 Collection
- 没有可渲染对象的 Collection
- 隐藏或禁用的对象
- 不支持的对象类型
- Collection 名称冲突
- 输出文件名冲突

---

## 9. 稳定颜色系统

### 9.1 颜色必须持久化

每个 Collection 保存：

```python
collection["cmask_uuid"]
collection["cmask_color"]
collection["cmask_role"]
collection["cmask_enabled"]
```

这样即使：

- Collection 改名
- Collection 调整顺序
- 工程保存后重新打开
- 新增其他 Collection

原有颜色仍不改变。

### 9.2 默认调色板

优先使用高区分度颜色：

```text
红、绿、蓝、黄、品红、青、
橙、紫、亮绿、亮蓝、粉红、浅黄
```

要求：

- 相邻组避免近似颜色
- 避免低饱和灰色
- 避免颜色过暗
- 超出预设数量后使用 HSV 等距生成
- 用户可以锁定或手动修改颜色

### 9.3 颜色分配原则

不使用 Collection 列表索引直接决定颜色，应通过 UUID 绑定颜色，避免插入新组后导致所有旧颜色变化。

---

## 10. 彩色 Collection ID 输出

### 10.1 推荐实现路线

创建插件专用覆盖材质：

```text
Object Info：Color
        ↓
Emission
        ↓
Material Output
```

导出前，将同一 Collection 中的对象临时设置为相同的 `object.color`。

然后通过专用 View Layer 的 `Material Override` 输出彩色 ID。

### 10.2 优点

- 不修改正式材质节点
- 不依赖场景灯光
- 不产生高光、阴影和材质纹理干扰
- 保留正常相机遮挡关系
- Eevee 渲染速度快
- 可同时显示多个 Collection 的不同颜色

### 10.3 彩色 ID 输出规则

```text
MASK Collection      → 对应稳定颜色
HOLDOUT Collection   → 透明洞
OCCLUDER Collection  → Holdout 或指定阻隔颜色
IGNORE Collection    → Exclude
World Background     → 透明
```

建议默认让 `OCCLUDER` 在彩色 ID 图中表现为透明阻隔，也可提供“显示为指定颜色”的可选模式。

---

## 11. 独立透明蒙版输出

每个启用的 `MASK` Collection 输出一张 RGBA PNG：

```text
Mask_外壳.png
Mask_屏幕.png
Mask_按键.png
Mask_金属.png
```

目标区域可选择：

- 白色 + Alpha
- 原组颜色 + Alpha
- 仅 Alpha 通道

第一版建议默认：

```text
RGB：纯白
Alpha：真实蒙版透明度
```

因为这种格式最适合 Photoshop 直接载入图层蒙版。

---

## 12. 抗锯齿与边缘处理

### 12.1 彩色 ID 图

彩色 ID 图的边缘会存在抗锯齿混色，因此应定位为：

- 快速识别
- 色彩范围粗选
- 组别预览

不能把纯色像素选择视为最终精确边缘。

### 12.2 独立 RGBA 蒙版

独立蒙版的 Alpha 通道是精确输出，应作为正式后期蒙版。

### 12.3 边缘扩张与收缩

v0.3 已实现：

```text
边缘调整：-32～32 px
正值：扩张
负值：收缩
```

当前实现直接处理渲染结果的 Alpha，使用可分离的滑动窗口最大值/最小值算法，
不依赖用户 Compositor，也不会改写用户节点树。处理后的 RGB 固定为白色，Alpha
保留抗锯齿灰度并完成扩张或收缩。彩色 ID 图不应用此设置。

---

## 13. 色彩管理

导出蒙版时临时设置：

```text
View Transform：Standard
Look：None
Exposure：0
Gamma：1
Film Transparent：开启
```

输出完成后恢复用户原设置。

### 13.1 输出格式

默认：

```text
格式：PNG
颜色：RGBA
位深：8 bit
压缩：15%
```

可选：

- 16-bit PNG
- 16-bit / 32-bit OpenEXR（单层 RGBA）
- 仅 Alpha

彩色 ID 一般使用 8-bit PNG 即可；精细 Alpha 蒙版可允许 16-bit。

---

## 14. 插件界面设计

位置：

```text
3D Viewport
→ N 面板
→ Collection Mask
```

建议界面：

```text
Collection Mask Exporter

扫描设置
[扫描模式：CM_ 前缀]
[前缀：CM_]
[包括子集合：✓]
[扫描 / 同步]

蒙版组
------------------------------------------------
✓ CM_外壳       [颜色]  MASK
✓ CM_屏幕       [颜色]  MASK
✓ CM_按键       [颜色]  MASK
✓ CM_前景玻璃   [颜色]  OCCLUDER
✓ CM_挖空区域   [颜色]  HOLDOUT
  灯光与辅助             IGNORE
------------------------------------------------

冲突规则
[优先级解析 / 严格报错]
[检查场景]

输出设置
[蒙版模式：可见区域]
[透明背景：✓]
[使用场景分辨率：✓]
[格式：PNG RGBA]
[位深：8 bit]
[输出目录：...]

操作
[预览彩色 ID]
[导出彩色 ID]
[导出选中组蒙版]
[批量导出全部蒙版]
[全部导出]

状态
已识别 5 个蒙版组
发现 1 个多重归属对象
上次导出：成功
```

---

## 15. 预览机制

### 15.1 临时渲染预览

点击“预览彩色 ID”后：

1. 保存当前状态。
2. 创建或更新临时 View Layer。
3. 应用覆盖材质和颜色。
4. 执行低采样 Eevee 渲染。
5. 在 Render Result 中显示。
6. 不写入磁盘。
7. 恢复用户场景。

### 15.2 视口预览

后续版本可提供“视口颜色预览”，将视口切换为 Material Preview 或 Rendered，并临时显示 Collection 颜色。

第一版优先实现渲染预览，结果更接近最终输出。

---

## 16. 非破坏性状态管理

插件运行时可能临时修改：

- 对象颜色
- View Layer
- Material Override
- Collection 的 Exclude/Holdout 状态
- 渲染引擎
- 渲染采样
- 输出路径
- 文件格式与位深
- Film Transparent
- 色彩管理
- 当前帧
- 当前相机

必须在操作前创建完整快照。

伪代码：

```python
state = capture_scene_state()

try:
    validate_scene()
    prepare_mask_environment()
    render_outputs()
finally:
    restore_scene_state(state)
```

### 16.1 强制恢复

插件面板必须提供：

```text
[恢复场景状态]
```

并在开始任务时保存一份临时恢复数据。

如果用户取消、脚本异常或渲染失败，也必须执行 `finally` 恢复。

---

## 17. 临时资源管理

所有插件生成资源使用固定前缀：

```text
__CMASK_VIEW_LAYER
__CMASK_MATERIAL
__CMASK_WORLD
__CMASK_COMPOSITOR
```

导出完成后根据设置：

- 删除临时资源
- 或保留并复用，提高下次导出速度

默认推荐“保留但隐藏”，减少重复创建节点和数据块。

---

## 18. 文件输出结构

默认目录：

```text
项目目录/
└─ CMask_Output/
   ├─ Color_ID/
   │  └─ product_collection_id.png
   ├─ Masks/
   │  ├─ product_mask_外壳.png
   │  ├─ product_mask_屏幕.png
   │  ├─ product_mask_按键.png
   │  └─ product_mask_金属.png
   └─ Reports/
      └─ product_cmask_report.json
```

### 18.1 文件命名模板

支持变量：

```text
{blend}
{scene}
{camera}
{collection}
{frame}
{mode}
```

默认模板：

```text
{blend}_{collection}_{mode}.png
```

### 18.2 文件名清理

自动处理：

- Windows 非法字符
- 中文名称
- 重复名称
- 空格与特殊符号
- 文件路径过长

内部识别使用 UUID，不依赖清理后的文件名。

---

## 19. 数据模型建议

### 19.1 Collection 自定义属性

持久化保存在 Collection：

```python
cmask_uuid: str
cmask_color: FloatVectorProperty
cmask_role: EnumProperty
cmask_enabled: bool
cmask_priority: int
```

### 19.2 Scene 插件配置

保存在 Scene：

```python
scan_mode
collection_prefix
include_children
conflict_mode
mask_output_mode
output_directory
file_format
color_depth
use_scene_resolution
transparent_background
```

### 19.3 UI 列表缓存

使用 `PropertyGroup + CollectionProperty` 建立界面列表，但 Collection 自定义属性作为真实数据源，避免列表刷新后配置丢失。

---

## 20. 推荐代码结构

```text
collection_mask_exporter/
├─ blender_manifest.toml
├─ __init__.py
├─ registration.py
├─ properties.py
├─ preferences.py
│
├─ core/
│  ├─ scanner.py
│  ├─ hierarchy.py
│  ├─ group_resolver.py
│  ├─ conflict_checker.py
│  ├─ color_manager.py
│  ├─ state_manager.py
│  ├─ layer_collection.py
│  ├─ material_override.py
│  ├─ render_pipeline.py
│  ├─ output_manager.py
│  └─ report_manager.py
│
├─ operators/
│  ├─ scan.py
│  ├─ validate.py
│  ├─ preview.py
│  ├─ export_color_id.py
│  ├─ export_selected_mask.py
│  ├─ export_all_masks.py
│  ├─ export_all.py
│  └─ restore_state.py
│
├─ ui/
│  ├─ panel.py
│  ├─ ui_list.py
│  └─ menus.py
│
└─ tests/
   ├─ fixtures/
   ├─ test_scanner.py
   ├─ test_nested_collections.py
   ├─ test_conflicts.py
   ├─ test_visible_mask.py
   ├─ test_silhouette_mask.py
   ├─ test_holdout.py
   ├─ test_output_names.py
   └─ test_state_restore.py
```

---

## 21. 核心处理流程

### 21.1 扫描流程

```text
读取扫描模式
    ↓
获取候选 Collection
    ↓
递归解析子集合
    ↓
过滤不可渲染对象
    ↓
检测多重归属
    ↓
读取或创建 UUID
    ↓
读取或创建稳定颜色
    ↓
更新插件列表
```

### 21.2 彩色 ID 导出流程

```text
保存场景状态
    ↓
创建/复用专用 View Layer
    ↓
解析每个对象最终所属蒙版组
    ↓
临时写入 object.color
    ↓
设置 Emission Material Override
    ↓
设置 MASK / HOLDOUT / OCCLUDER / IGNORE
    ↓
设置透明背景和 Standard 色彩管理
    ↓
渲染彩色 ID PNG
    ↓
恢复场景状态
```

### 21.3 独立蒙版导出流程

```text
保存场景状态
    ↓
遍历所有启用的 MASK Collection
    ↓
将目标组设置为白色
    ↓
根据 VISIBLE 或 SILHOUETTE 配置其他组
    ↓
渲染 RGBA PNG
    ↓
记录结果与异常
    ↓
处理下一个组
    ↓
恢复场景状态
```

---

## 22. 对象类型支持

### v0.1 支持

- Mesh
- Curve
- Surface
- Text
- Meta
- Volume（基础支持）
- 可正常渲染的实例对象

### v0.1 有限支持

- Collection Instance：先作为整体处理
- Geometry Nodes：按宿主对象所属 Collection 处理
- 粒子实例：按发射对象或实例对象策略处理
- Grease Pencil：视 Blender 版本进行兼容测试

### 暂不支持

- Geometry Nodes 内每个实例独立 Collection ID
- 一个对象内部按几何组件分组
- 玻璃折射后被看见对象的精确语义蒙版
- 深度学习语义分割

---

## 23. 性能策略

### 23.1 渲染引擎

默认使用 Eevee 进行蒙版渲染。

原因：

- Emission 覆盖材质不需要复杂光照
- 输出速度快
- 足以保留相机遮挡和 Alpha
- 产品静帧通常只需一次或少量批量渲染

### 23.2 资源复用

- 复用专用 View Layer
- 复用覆盖材质
- 仅更新变化的对象颜色
- 缓存 Collection 到对象映射
- 批量导出期间不重复扫描完整场景

### 23.3 大场景优化

当前进度：

- [x] 仅扫描当前可见 View Layer
- [x] 增量同步
- 按依赖图变化重新解析
- 跳过未改变 Collection
- 后台命令行批量导出

---

## 24. 异常处理

必须处理：

1. 没有活动相机。
2. 输出目录不可写。
3. Collection 为空。
4. 对象多重归属。
5. 临时材质创建失败。
6. View Layer 创建失败。
7. 渲染被用户取消。
8. 文件名重复。
9. 场景未保存且使用相对路径。
10. Blender 版本不兼容。
11. 对象被禁用渲染。
12. 导出过程中对象或 Collection 被删除。

错误信息应包含：

```text
问题对象或 Collection
问题原因
是否跳过
建议处理方式
```

不能只显示 Python Traceback。

---

## 25. 日志与报告

每次导出生成可选 JSON 报告：

```json
{
  "scene": "Scene",
  "camera": "Camera",
  "mode": "VISIBLE",
  "groups": 5,
  "success": 4,
  "failed": 1,
  "conflicts": [
    {
      "object": "Logo_Object",
      "collections": ["CM_Logo", "CM_外壳"],
      "resolved_to": "CM_Logo"
    }
  ]
}
```

界面状态区域显示：

```text
导出成功：4
导出失败：1
跳过：0
耗时：12.4 秒
```

---

## 26. MVP 验收标准

v0.1 必须满足：

1. Collection 与颜色绑定稳定。
2. Collection 改名后颜色不变。
3. 彩色 ID 图与正式渲染的构图、分辨率一致。
4. 同一 Collection 的全部对象使用相同颜色。
5. `VISIBLE` 模式能正确保留前后遮挡。
6. `SILHOUETTE` 模式能输出完整轮廓。
7. HOLDOUT 区域能正确切出透明部分。
8. 每个 MASK Collection 能输出独立 RGBA PNG。
9. 嵌套 Collection 按“子组优先”规则解析。
10. 多重归属能够警告、自动解析或严格中止。
11. 中文 Collection 名称可以正常导出。
12. 导出结束后正式材质和场景设置不被破坏。
13. 用户取消渲染后仍能恢复场景。
14. Blender 4.5 LTS、5.0 和 5.2 测试通过。

---

## 27. 测试场景设计

### 测试 A：基础分组

```text
CM_Red
CM_Green
CM_Blue
```

验证颜色、文件名和独立蒙版。

### 测试 B：前后遮挡

前景立方体遮挡后方球体。

验证：

- VISIBLE：球体被遮住部分透明
- SILHOUETTE：球体完整显示

### 测试 C：Holdout

一个切割物体位于目标组前方。

验证结果区域是否为透明洞。

### 测试 D：嵌套集合

父级 MASK 包含一个显式子级 MASK。

验证子组优先且不重复。

### 测试 E：多重归属

一个对象链接到两个 MASK Collection。

验证优先级模式和严格模式。

### 测试 F：异常恢复

在批量导出中途主动取消。

验证对象颜色、渲染引擎、输出路径和 View Layer 完整恢复。

---

## 28. 版本规划

### v0.1：核心可用版

- Collection 扫描
- 稳定颜色
- 角色设置
- 彩色 ID 输出
- VISIBLE 独立蒙版
- SILHOUETTE 独立蒙版
- Holdout 与 Occluder
- 批量导出
- 状态恢复
- 冲突检查

### v0.2：效率增强版

- [x] 边缘扩张/收缩
- [x] 16-bit PNG
- [x] 输出命名模板
- [x] 预设保存
- [x] 多相机批量输出
- [x] 动画帧范围
- [x] Outliner 右键菜单
- [x] 增量同步
- [x] JSON 导出报告

### v0.3：合成增强版

- [x] 单层 RGBA OpenEXR 16/32-bit
- [x] Multilayer EXR
- [x] Cryptomatte 集合聚合
- [x] Blender Compositor 自动节点
- [x] 每组输出独立通道
- [x] Alpha 预乘模式设置
- [x] 透明材质策略
- [x] 仅扫描当前可见 View Layer

### v1.0：生产版

- [x] Geometry Nodes 实例增强支持（宿主整体语义与静态源解析）
- [x] 单个 Geometry Nodes 宿主内部静态源组拆分
- [x] Collection Instance 深层解析
- [x] 命令行与渲染农场支持
- [x] Photoshop 导入脚本
- [x] 自动创建 PSD 图层的辅助工具
- [x] 自动创建 Photoshop Alpha 通道
- [x] 完整文档、示例工程和自动测试

---

## 29. 第一阶段开发任务拆分

### 阶段 1：技术验证

1. 使用 Material Override 读取 Object Info Color。
2. 验证 Eevee 下纯色和 Alpha 是否稳定。
3. 验证 LayerCollection 的 Exclude、Holdout。
4. 验证中途取消后的状态恢复。
5. 验证嵌套 Collection 递归解析。

### 阶段 2：核心模块

1. Collection 扫描器。
2. UUID 与颜色管理。
3. 对象归属解析器。
4. 冲突检查器。
5. 状态快照与恢复。
6. 单张彩色 ID 渲染。

### 阶段 3：独立蒙版

1. VISIBLE 模式。
2. SILHOUETTE 模式。
3. HOLDOUT 和 OCCLUDER。
4. 文件命名与批量导出。
5. 取消与错误恢复。

### 阶段 4：UI 与交付

1. N 面板。
2. Collection UIList。
3. 颜色和角色编辑。
4. 输出设置。
5. 日志和错误提示。
6. 打包为 Blender Extension。

---

## 30. 最终推荐技术路线

```text
Collection 自定义配置
        ↓
扫描层级和解析对象归属
        ↓
UUID 绑定稳定颜色
        ↓
对象临时写入 Collection Color
        ↓
专用 View Layer
        ↓
Object Info Color
        ↓
Emission Material Override
        ↓
Exclude / Holdout 控制遮挡
        ↓
Eevee 快速渲染
        ↓
彩色 ID + 独立 RGBA 蒙版
        ↓
完整恢复用户场景
```

---

## 31. 项目实施建议

该插件不应仅定位为“又一个 Object ID 工具”，而应强调：

> **以 Collection 为核心的 Blender 到 Photoshop 蒙版交付流程。**

最重要的差异化功能是：

1. Collection 直接作为蒙版组。
2. 同组对象自动同步。
3. 稳定颜色不会随场景顺序变化。
4. 同时输出彩色 ID 和精确 RGBA 蒙版。
5. 明确区分真实可见蒙版与完整轮廓蒙版。
6. 支持透明阻隔与纯遮挡物。
7. 导出后不污染正式场景。

第一版开发中，必须优先验证“遮挡结果正确”和“场景能够完整恢复”。只有这两项稳定后，再扩展 Cryptomatte、EXR、动画和 Photoshop 自动化。
