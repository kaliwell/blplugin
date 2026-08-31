# CMask 实现状态与使用说明

> 插件版本：v0.10.1
> 正式支持：Blender 4.5.x、5.0.x、5.2.x
> 验证版本：4.5.12、5.0.1、5.2.0

项目接手、发布物、代码结构、测试命令和下一阶段计划见
[CMask_项目交接与当前进度.md](CMask_项目交接与当前进度.md)。

## 1. 当前已实现

### Collection 管理

- `CM_` 名称前缀递归扫描。
- Scene Collection 顶级集合扫描。
- 手动选择、添加和移除 Collection。
- 列表上下移动并持久化冲突解析优先级。
- 子组优先规则，支持跨非显式中间层的深层显式子组。
- UUID、颜色、角色、启用状态和优先级持久化。
- `MASK`、`HOLDOUT`、`OCCLUDER`、`IGNORE` 四种角色。
- 增量扫描只增删、移动发生变化的行，并保持现有行数据和选中 Collection。
- 名称前缀和顶级集合扫描可只包含当前 View Layer 中可见的 Collection；
  被父级排除的深层 Collection 也会一起过滤。
- Outliner 的 Collection 右键菜单可直接加入 CMask 手动管理。
- Collection Instance 按宿主所属组作为整体处理，并递归解析嵌套实例源。
- 实例源 Collection 可继续链接在场景并从活动 View Layer 排除；导出时会保留
  排除状态，同时保证实例副本正常参与彩色 ID 和独立蒙版。
- Geometry Nodes 宿主按所属 CMask 组作为整体处理；直接设置的 Collection Info
  和 Object Info 源、嵌套节点组以及递归 Geometry Nodes 源会被静态解析。
- Geometry Nodes 源可链接在场景并从活动 View Layer 排除；渲染管线保护它们的
  `hide_render`、材质和 Holdout 状态，避免节点实例在导出期间消失。
- 可选“拆分 Geometry Nodes 静态源”：IGNORE 宿主直接引用的显式 MASK 源组
  可在同一宿主内部独立导出，不会修改或复制用户节点树。
- Blender 5.0+ 可选求值后 `cmask_id` 动态字段：驱动、Simulation Zone、
  Repeat Zone 或字段结果可在最终 FACE/INT 属性上按 ID 独立导出。
- 面板、属性、操作与主要运行状态跟随 Blender 自动切换简体中文 / English。
- 3D 视图侧栏使用 Blender 原生父级/子级可折叠面板，并记忆各功能区展开状态。
- “一键配置 GN 静态源拆分”会自动识别宿主、重新启用宿主、设置 IGNORE 并
  开启拆分；场景检查会阻止宿主角色错误，并提示没有可用 MASK 源组的配置。
- GN 静态依赖只扫描能够到达节点组输出的路径；嵌套节点组只追踪外层实际使用
  的输出插口，未连接的实验/备用 Info 节点不会改变归属或触发一键配置。
- 拆分模式的彩色 ID 由各 MASK 的 VISIBLE 覆盖率合成，支持 8/16-bit PNG、
  16/32-bit EXR、Multilayer EXR 和 Collection Cryptomatte。

### 场景预设

- 在当前 `.blend` 内保存、覆盖、应用和删除命名预设。
- 保存扫描、冲突、蒙版、格式、位深、边缘、命名、报告和批量设置。
- 按 Collection UUID 保存组顺序、启用状态、角色与颜色。
- 应用到 Collection 有变化的场景时按 UUID 匹配，并以名称作为兼容后备。
- 缺失 Collection 会跳过并在状态栏报告数量，不会阻止其余设置应用。

### 检查与冲突处理

- 空 Collection 检查。
- 多重对象归属检查。
- 严格报错和按列表优先级解析。
- 面板内显示问题对象、问题类型和说明。

### 渲染与输出

- 彩色 Collection ID 预览和导出。
- 选中 MASK 组预览与导出。
- 全部 MASK 组批量导出。
- 彩色 ID 与全部蒙版一键导出。
- `VISIBLE`：保留其他组的真实遮挡。
- `SILHOUETTE`：输出目标组完整轮廓。
- Alpha 边缘扩张/收缩，范围为 `-32` 到 `32` 像素；正值扩张，负值收缩。
- 默认保持精确 Alpha 边界；需要特殊补边时可开启“蒙版扩张 1 像素（可选）”；
  用户明确设置负值收缩时不会叠加自动补偿。
- 可按选中 MASK 组或全部 MASK 组直接输出 `Cutouts`：保留目标原始材质，
  其他组继续参与真实遮挡，但遮挡区域直接写为透明，不再二次套蒙版。
- 8-bit、16-bit RGBA PNG，以及 16-bit、32-bit RGBA OpenEXR。
- 当前相机或场景全部相机批量导出。
- 当前帧或自定义起止帧、步长批量导出。
- 当命名模板未包含相机或帧变量时，自动追加相机/帧后缀避免覆盖。
- `Straight` Alpha：RGB 保持白色，Alpha 独立存储。
- `Premultiplied` Alpha：RGB 乘以 Alpha，适合预乘合成工作流。
- 透明材质可选择“视为实体”或“排除对象”。
- 可在导出后自动将最近输出载入 Compositor 的 CMask Frame。
- 可随时用“载入最近输出到合成器”刷新插件生成的图像节点。
- 单文件 Multilayer EXR，每个启用的 MASK 对应独立 `R/G/B/A` 层。
- Multilayer EXR 可选择是否包含 `Color_ID` RGBA 层。
- 位深选择 `32 bit` 时写入 float，其余选择写入 half。
- Collection Cryptomatte 使用标准 `CryptoCollection00` 等 ID/coverage 通道，
  内嵌 MurmurHash3_32 manifest，可在兼容 Cryptomatte 的合成软件中按
  Collection 名称选择。
- Cryptomatte 固定使用 32-bit float，可配置每像素保存 2–12 个 Collection；
  为保持语义正确，它固定使用 VISIBLE 覆盖率且不应用边缘扩张/收缩。
- 透明背景、Standard 视图变换和 Emission 覆盖材质。
- 自动创建 `Color_ID`、`Masks`、`Cutouts` 和 `Reports` 目录。
- 对象或 Collection 右键可进入单独渲染：目标正常渲染，其他可见对象作为
  透明 Holdout 遮挡；主面板和右键菜单均可取消并精确恢复进入前状态。

### 非破坏性处理

- 临时 View Layer 和材质使用每次操作唯一的 UUID 名称。
- 导出期间临时禁用用户 Compositor 和 Sequencer。
- 继承活动 View Layer 的 Collection Exclude 状态。
- 尊重对象原始 `hide_render` 状态。
- 恢复渲染引擎、输出设置、色彩管理、对象颜色、Holdout、材质槽、
  View Layer 启用状态和活动 View Layer。
- 对渲染期间被删除的数据块采用逐项容错恢复。

### 命令行与渲染农场

- 通过 Blender `--background` 和 `collection_mask_exporter.cli.main()` 执行。
- 支持彩色 ID、选中蒙版、全部蒙版、选中/全部透明抠图、全部导出、批量、Multilayer EXR 和
  Collection Cryptomatte 操作。
- 支持 JSON 任务文件，并允许显式命令行参数覆盖任务字段。
- 可选择场景和场景内预设，覆盖输出目录、扫描、格式、相机与帧范围设置。
- 标准输出包含单行 `CMASK_CLI_RESULT=<JSON>`，也可写独立结果 JSON。
- 失败时输出结构化错误并以非零状态退出；不会自动保存输入 `.blend`。

### Photoshop 交付

- 根据 `last_outputs` 中的最近导出结果生成自包含 Photoshop JSX。
- 同时生成 `cmask.photoshop_handoff.v1` JSON 清单，记录源文件、图层名、
  脚本路径和目标 PSD 路径。
- Photoshop 脚本逐项校验源文件，将 `Color_ID` 和 `Masks` 输出转换为清晰的
  命名图层，并自动保存带图层的 PSD。
- 默认让蒙版文件、Photoshop 图层和 Alpha 通道直接使用 Collection 组名；
- 蒙版 RGB 与同组 Color ID 颜色一致，Alpha 仍保留精确覆盖率；
- 一键生成正式渲染、Color ID、全部蒙版、全部透明抠图、Photoshop JSX 和交接清单；
- 可将每个 `Masks` 图层的透明度选区写入独立同组名 Alpha 通道；
  通道名会自动消解重复，PSD 保存时显式保留 Alpha 通道。
- “Photoshop 创建 Alpha 通道”可关闭，并可随场景预设保存。
- JSX 使用带 BOM 的 UTF-8，支持中文 Collection 名称和 Windows 路径。

### 示例工程与教程

- `examples/CMask_Demo.blend` 兼容 Blender 4.5、5.0、5.2 正式支持版本。
- 示例包含两个 MASK、一个 OCCLUDER、一个 HOLDOUT、正交相机和完整交付预设。
- `tests/create_sample_project.py` 可重复生成示例，避免二进制工程与代码脱节。
- 示例验收会执行场景检查、彩色 ID、独立蒙版、JSON 报告和 Photoshop 交接。

### Blender API 兼容性诊断

- 面板“API 兼容性诊断”会检查当前运行环境并写入结构化 JSON。
- 检查临时 View Layer、材质覆盖、LayerCollection 标志、图像格式、版本化
  Compositor API 和 OpenImageIO。
- 必需能力缺失会使诊断失败；可选能力缺失只影响对应高级功能。
- Blender 6.0+ 在完成正式版本矩阵前标记为 `FUTURE_UNVALIDATED`。
- CLI 支持 `--operation diagnose`，结果 JSON 的 `diagnostic_report` 返回报告路径。

## 2. 基本工作流

1. 在 3D Viewport 打开右侧 N 面板。
2. 进入 `Collection Mask` → `Collection Mask Exporter`。
3. 可先输入预设名称并应用已有场景预设。
4. 选择扫描模式：名称前缀、顶级集合或手动选择；大场景可启用“仅扫描当前
   View Layer 可见集合”。
5. 点击“扫描 / 同步”。
6. 设置各组颜色、角色和启用状态。
7. 使用“提高优先级 / 降低优先级”处理多重归属顺序。
8. 如需拆分 Geometry Nodes 静态源，点击“一键配置 GN 静态源拆分”。
9. 点击“检查场景”，处理错误和警告。
10. 设置蒙版模式、边缘调整、格式、位深、命名模板和输出目录。
11. 如需批量任务，设置相机范围以及帧范围和步长。
12. 需要复用时保存或覆盖场景预设。
13. 预览或执行单项、批量、全部导出。
14. 需要交给 Photoshop 时，点击“生成 Photoshop 导入脚本”，然后在
    Photoshop 的“文件 → 脚本 → 浏览”中运行生成的 `.jsx`。

启用“导出后创建合成节点”时，成功导出后会开启场景 Compositor，并创建一个
“CMask 最近输出”Frame。再次生成只会替换带有 CMask 标记的节点，不会删除或
连接用户已有节点。Blender 4.x 使用 Scene Node Tree，Blender 5.x 使用新的
Compositing Node Group，插件会自动选择对应 API。

“导出 Multilayer EXR”会在临时目录渲染彩色 ID 和各组蒙版，再按
`Collection.R/G/B/A` 通道名合并为一个 EXR。临时文件会自动删除，最终文件
直接放在输出根目录。层名中的特殊字符会替换为下划线，重名会追加数字。
当前该按钮处理活动相机和当前帧；多相机/帧范围仍由批量独立文件功能处理。

“导出 Collection Cryptomatte”会渲染所有启用的 MASK 组，并按每个像素的
覆盖率从高到低写入标准 ID/coverage 对。输出根目录中的 EXR 内嵌 Collection
名称 manifest，可直接交给 Blender、Nuke 等兼容 Cryptomatte 的合成器。
该按钮当前处理活动相机和当前帧；导出完成后会恢复格式、位深、蒙版模式、
边缘调整和 Alpha 设置。

“生成 Photoshop 导入脚本”使用最近一次成功导出的文件，不会重新渲染。
生成结果位于输出目录的 `Photoshop` 子目录：`*_import.jsx` 是导入脚本，
`*_handoff.json` 是交接清单；运行脚本后 `*.psd` 写入同一目录。为了避免
Photoshop 图层位深不兼容，建议同一批输出使用相同格式和位深。

“导出选中组透明抠图”和“批量导出全部透明抠图”直接使用目标对象的原材质与
当前渲染引擎。`VISIBLE` 模式保留其他组的真实遮挡并把遮挡部分写成透明；
`SILHOUETTE` 模式忽略其他组，输出目标完整轮廓。一键交付默认包含全部抠图，
可用“一键交付包含透明抠图”关闭。

在 3D 视图对象右键菜单或 Outliner 的对象/Collection 右键菜单中选择“单独渲染”
会立即渲染，并保持该状态以便继续按 F12。此时其他原本可见的几何体不会消失，
而是作为透明遮挡参与深度关系。使用主面板醒目的“取消单独渲染”或右键菜单
同名命令，可恢复进入前的 `hide_render`、Holdout、View Layer 和透明背景设置。

手动模式下，先在 `Collection` 字段中选择集合，再点击“添加 Collection”。
从列表移除只取消插件管理，不会删除 Blender Collection，也不会清除它已经
保存的 CMask 元数据。

在 Outliner 中右键 Collection，选择“添加到 CMask（手动模式）”可快速加入。
此操作会保留当前列表并切换为手动模式。预设随 `.blend` 保存；保存预设时，
相对输出目录会解析为当前工程对应的绝对路径，避免跨 Blender 版本赋值警告。

## 3. 命名模板

默认模板：

```text
{blend}_{collection}_{mode}
```

支持变量：

| 变量 | 含义 |
|---|---|
| `{blend}` | `.blend` 文件名，不含扩展名 |
| `{scene}` | 当前 Scene 名称 |
| `{camera}` | 活动相机名称 |
| `{collection}` | Collection 名称；彩色 ID 使用 `collections` |
| `{frame}` | 四位当前帧号 |
| `{mode}` | `color_id`、`visible` 或 `silhouette` |

插件会处理 Windows 非法字符、保留设备名以及批量任务中清理后的重名；发生
重名时使用 Collection UUID 短后缀，避免静默覆盖。多相机/多帧任务如果模板
仍产生相同路径，会自动追加 `{camera}_{frame}` 形式的后缀。

## 4. JSON 报告

启用“写入 JSON 报告”后，每类导出在 `Reports` 中生成独立报告，记录：

- Blender、Blend、Scene 和 Camera。
- 操作类型、蒙版模式、输出格式、位深、边缘调整、Alpha 模式和透明材质策略。
- 成功状态、错误和耗时。
- 输出文件列表。
- 场景检查问题。
- 多重归属及最终解析结果。
- 实例源同时被其他 CMask 组管理时的冲突。
- Geometry Nodes 静态实例源、无法静态解析的动态输入及源组冲突。

报告按操作类型命名；重复执行同一种操作会更新该操作的最新报告。

## 5. 当前限制

- v0.7.0 起正式支持矩阵仅包含 Blender 4.5.x、5.0.x、5.2.x；扩展清单最低
  安装版本为 4.5.0。其他版本线不再作为发布验收目标。
- Geometry Nodes 默认按宿主对象/整体处理。静态模式解析直接设置的
  Collection/Object Info；Blender 5.0+ 动态模式读取最终 Mesh 的 FACE/INT
  `cmask_id`。若动态结果未写入该属性，仍不能推断其业务归属。
- 拆分模式要求宿主组为 IGNORE，源集合为显式 MASK；可使用一键配置处理宿主，
  源集合因 View Layer
  排除而无法被“仅扫描可见集合”发现时，应关闭该扫描选项或手动添加。
- 拆分彩色 ID 暂不写入 Render Result 预览，应使用导出文件检查结果。
- Collection Instance 以宿主组作为完整语义单元，不会把一个实例内部的不同
  源 Collection 拆成多个独立 CMask 组。
- “排除透明材质”是对象级保守策略：任一材质声明透明即排除整个对象，不解析
  纹理 Alpha 的逐像素覆盖。
- 不提供玻璃折射后的语义级遮挡解析。

## 6. 回归验证

自动测试覆盖：

- 扫描与稳定颜色。
- 角色和启用状态持久化。
- 两层及深层显式子组优先。
- 多重归属与严格模式。
- 手动组增删和优先级移动。
- 增量同步的行数据、顺序和选中项保持。
- 当前 View Layer 的排除、隐藏和父级排除扫描过滤。
- CLI JSON 任务解析、显式参数覆盖、成功/失败结果和实际后台导出。
- 两层 Collection Instance、场景内已排除实例源、独立左右蒙版、透明材质
  排除、实例源组冲突以及源对象状态恢复。
- Geometry Nodes Collection/Object Info 静态依赖、动态输入警告、跨组源冲突、
  View Layer 已排除源、双宿主独立 ID/蒙版、透明源排除和状态恢复。
- 单宿主双静态源拆分彩色 ID、独立蒙版、Multilayer EXR、Cryptomatte、
  一键配置、错误角色拦截、跨组冲突豁免、预设往返及状态恢复。
- 示例工程的四种角色、场景预设、真实全部导出、报告和 Photoshop 脚本生成。
- API 兼容性必需/可选能力、报告写入、面板操作及 CLI `diagnose`。
- 场景预设保存、覆盖应用与删除。
- Outliner 快捷加入手动组。
- 输出命名和冲突消解。
- 用户同名临时资源保护。
- 隐藏对象和 View Layer Exclude。
- 删除数据块后的容错恢复。
- 彩色 ID、VISIBLE 和 SILHOUETTE 实际渲染。
- 16-bit PNG 文件头。
- Alpha 扩张与收缩后的像素面积变化。
- Straight 与 Premultiplied 的实际边缘 RGB/Alpha 像素关系。
- 透明材质视为实体和排除对象的实际渲染差异。
- Blender 4.x/5.x Compositor 图像节点生成及重复更新。
- Photoshop JSX 的路径转义、中文图层名、UTF-8 BOM、Alpha 通道动作和交接 JSON。
- 32-bit OpenEXR 文件输出。
- half/float Multilayer EXR 写入与独立命名 RGBA 通道。
- MurmurHash3 标准向量、Cryptomatte manifest、32-bit ID/coverage 通道及
  实际 Collection 覆盖率导出。
- 多相机、帧范围、路径冲突消解以及相机/帧恢复。
- JSON 报告内容。
- 用户材质、合成器、序列器和 View Layer 状态恢复。

`未命名.blend` 已在 Blender 4.5.12、5.0.1、5.2.0 上完成彩色 ID、
10 张独立蒙版和 1 个六层 Multilayer EXR 的真实导出验证。
