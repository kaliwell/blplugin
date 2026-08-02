# Collection Mask Exporter (CMask)

当前开发版本：v0.9.0。更新扩展后需要完整退出并重新启动 Blender，
否则旧 Python 模块可能继续驻留在当前进程中。

面向 Blender 4.5.x、5.0.x、5.2.x 的 Collection 蒙版导出扩展，当前已经包含：

- 按 `CM_` 前缀或顶级 Collection 扫描
- Collection UUID 与颜色持久化
- MASK / HOLDOUT / OCCLUDER / IGNORE 角色
- 嵌套 Collection 的显式子组优先规则
- 多重归属、空集合与重名检查
- 3D 视图侧栏的“Collection Mask”面板
- 彩色 Collection ID 预览与 PNG 导出
- VISIBLE / SILHOUETTE 独立 RGBA 蒙版
- 选中组、全部蒙版和一键全部导出
- Alpha 边缘扩张与收缩
- PNG 8/16-bit 与 OpenEXR 16/32-bit 输出
- 当前/全部相机和当前帧/帧范围批量导出
- 场景内预设保存、应用与删除
- 保留现有列表项和选中项的增量同步
- 可选仅扫描当前 View Layer 中可见的 Collection
- Outliner Collection 右键快捷加入手动管理
- Straight / Premultiplied Alpha 存储
- 透明材质视为实体或按对象排除
- 将最近输出自动载入 Blender Compositor
- 单文件 Multilayer EXR，每个 MASK 独立 RGBA 层
- 标准 Collection Cryptomatte EXR，内嵌名称与 ID manifest
- 后台命令行与 JSON 渲染农场任务
- Collection Instance 宿主归属与嵌套源 Collection 解析
- Geometry Nodes Collection/Object Info 静态实例源解析
- 单个 Geometry Nodes IGNORE 宿主内部静态 MASK 源拆分
- Blender 5.0+ 求值后 `cmask_id` 动态字段拆分，支持驱动与 Zone 输出
- 跟随 Blender 界面语言自动切换简体中文 / English
- Photoshop JSX 交接脚本、分层 PSD 与 Alpha 通道自动创建
- 组名蒙版、Color ID 同色 RGB，以及渲染/蒙版/Photoshop 一键交付
- Blender 原生父级/子级可折叠面板，减少侧栏按钮堆叠
- Blender 4.5/5.0/5.2 示例工程、快速入门和跨版本验收脚本
- Blender API 一键兼容性诊断及渲染农场诊断任务
- 渲染结束或失败后的场景状态恢复

当前渲染管线使用临时 View Layer、Emission Material Override 和
Layer Collection 的 Exclude/Holdout 状态，不会替换正式材质。

v0.1.3 会在导出期间禁用用户合成器、序列器和正式 View Layer，并为
Blender 4.5 的新版本工程兼容问题临时覆盖数据材质槽；所有状态和正式材质
都会在导出结束或异常时恢复。

v0.1.4 修复审计发现的问题：重新扫描保持角色和启用状态，显式深层
Collection 正确覆盖祖先归属，临时材质和 View Layer 使用唯一名称，恢复
流程可跳过渲染期间被删除的数据块，VISIBLE 模式继承对象和活动 View Layer
的可见性，批量导出会自动消解清理后的文件名冲突。

v0.2.0 新增手动 Collection 管理、组优先级调整、详细检查结果、选中组
蒙版预览、8/16-bit PNG、命名模板和 JSON 导出报告。

v0.3.0 新增 Alpha 边缘扩张/收缩、OpenEXR 16/32-bit、当前/全部相机、
当前帧/帧范围批量导出，并自动消解相机和帧组合造成的路径冲突。

v0.3.1 新增场景内交付预设、增量扫描同步和 Outliner Collection 右键入口。

v0.3.2 新增 Alpha 预乘模式、透明材质对象级策略，以及兼容 Blender 4.x
和 5.x 两套节点 API 的 Compositor 图像节点自动生成。

v0.3.3 新增 Multilayer EXR：可选彩色 ID，并为每个启用的 MASK 写入独立
RGBA 层；16-bit 使用 half，32-bit 使用 float。

v0.3.4 新增“仅扫描当前 View Layer 可见集合”：名称前缀和顶级集合扫描可
忽略当前 View Layer 中被排除或隐藏的 Collection，并可随场景预设保存。

v0.3.5 新增 Collection Cryptomatte：将各 MASK 的可见覆盖率写入标准 32-bit
ID/coverage 通道，使用 MurmurHash3_32 和内嵌 manifest，深度可选 2–12。

v0.4.0 新增后台命令行入口与 JSON 任务文件：可选择场景、预设和导出操作，
覆盖输出、扫描、相机、帧范围等设置，并写出适合农场调度器读取的结果 JSON。

v0.4.1 新增 Collection Instance 深层依赖解析：实例宿主可作为完整蒙版组，
嵌套实例、被 View Layer 排除的场景内源 Collection、透明材质策略和状态恢复
均受支持；实例源同时被其他 CMask 组管理时会报告冲突。同时避免在 Blender
5.2 上无必要地调用预计由 6.0 移除的 `Material.use_nodes`。

v0.4.2 新增 Photoshop 自动交付：根据最近输出生成自包含 JSX 和 JSON 清单；
在 Photoshop 中运行脚本后，会把彩色 ID 与蒙版建立为命名图层并保存分层 PSD。

v0.4.3 可将 `Masks` 输出图层的透明度自动保存为命名 Alpha 通道；该行为可在
面板关闭并随场景预设保存，PSD 保存时会显式保留图层和 Alpha 通道。

v0.4.4 新增 Geometry Nodes 静态实例源解析：支持直接 Collection Info、
Object Info、嵌套节点组和递归节点宿主依赖；被 View Layer 排除的源仍可正常
生成宿主 ID/蒙版，透明材质、跨组冲突、动态输入警告和状态恢复均已覆盖。

v0.4.5 新增 `examples/CMask_Demo.blend`：内置 MASK、OCCLUDER、HOLDOUT、
16-bit PNG、JSON 报告、Photoshop 交付和“演示交付”预设；示例由脚本生成并
提供跨版本真实导出验收。

v0.4.6 新增 API 兼容性诊断：检查临时 View Layer、材质覆盖、LayerCollection、
图像格式、Compositor 和 OpenImageIO，输出 `cmask.compatibility.v1` JSON；
面板和 CLI `diagnose` 均可调用，Blender 6.0+ 会明确标记为尚未正式验证。

v0.5.0 新增 Geometry Nodes 静态源拆分：将宿主组设为 IGNORE，并启用拆分后，
直接 Collection Info/Object Info 引用的显式 MASK 组可在同一宿主内部得到独立
蒙版、彩色 ID、Multilayer EXR 层和 Cryptomatte 名称，且不改写用户节点树。

v0.5.1 新增“一键配置 GN 静态源拆分”，自动识别有显式静态源的宿主并设置为
IGNORE；场景检查会阻止宿主角色错误造成的静默误导输出，界面也会禁用拆分模式
下尚不支持的彩色 ID Render Result 预览。

v0.5.2 根据发布审计收紧 GN 静态分析：只识别能够到达节点组输出的节点，避免
未连接的实验节点触发拆分；一键配置现在也能重新启用已禁用的宿主，并明确区分
“关键 API 可用”与“Blender 版本正式受支持”。

v0.5.3 继续收紧嵌套节点组解析：只沿外层实际连接的节点组输出追踪内部依赖，
嵌套组中未被使用的备用输出不会再触发冲突检查或一键拆分配置。

v0.6.0 新增 Blender 5.0+ 求值后动态 GN 属性协议：用户在 Geometry Nodes 中
将整数 `cmask_id` 写入 FACE 域，CMask 会在每次渲染时读取最终几何并按 ID 拆分，
因此可承接驱动、Simulation Zone、Repeat Zone 等无法静态分析的结果。新增简体中文
和英文界面，语言自动跟随 Blender；动态配置也纳入预设、CLI、报告和场景检查。

v0.6.1 修复 Blender 5.2 中预设搜索控件参数不兼容导致面板只绘制到“预设”的问题。

v0.6.2 将已移除的 `MOD_NODES` 图标替换为 `GEOMETRY_NODES`，并新增跨版本
面板图标枚举检查，修复输出设置位置继续中断绘制的问题。

v0.6.3 兼容部分 Photoshop 版本拒绝恢复 `app.displayDialogs` 的行为，避免
PSD 已生成后仍在 JSX 收尾阶段报告“命令设置当前不可用”。

v0.6.4 针对会把 `app.displayDialogs` 错误置于 JavaScript `try/catch` 之外处理的
Photoshop 版本，彻底移除 JSX 对全局对话框模式的读取和修改。

v0.6.5 在创建 Alpha 通道前显式恢复复合颜色通道、清空选择并引用实际复制图层，
改用 stringID 透明度 Action；单个 Alpha 失败时继续保存分层 PSD 并列出失败项。

v0.6.6 将完全透明的空蒙版作为正常语义处理，直接创建全黑 Alpha 通道，不再
对空图层调用 Photoshop 不支持的“载入透明度”命令。

v0.7.0 收紧正式支持矩阵，仅保留 Blender 4.5.x、5.0.x、5.2.x；扩展安装最低
版本提高到 4.5，其他版本线即使关键 API 可用也会在诊断中标记为未正式验证。

v0.8.0 默认让蒙版文件、Photoshop 图层和 Alpha 通道直接使用 Collection 组名，
蒙版 RGB 与该组 Color ID 颜色一致；新增“一键导出渲染 + 蒙版 + Photoshop”，
一次生成正式渲染、Color ID、全部独立蒙版、JSX 和交接清单。

v0.8.1 补齐 Blender `Operator` 翻译上下文，修复按钮仍显示英文的问题；面板标题、
透明度存储方式以及旧场景未保存的默认预设占位也完成中文界面适配。

v0.9.0 将单一长侧栏重构为 Blender 原生父级/子级面板；扫描与组、输出设置、
一键交付默认展开，预设、检查、Geometry Nodes、批量、单项导出和高级输出默认折叠。

命令行与渲染农场用法见 `docs/CMask_命令行与渲染农场.md`。
Photoshop 交付用法见 `docs/CMask_Photoshop_交付.md`。
完整演示见 `examples/CMask_Demo.blend` 和
`docs/CMask_快速入门与示例工程.md`。
API 检查字段见 `docs/CMask_兼容性诊断.md`。
Geometry Nodes 拆分配置见 `docs/CMask_Geometry_Nodes_静态源拆分.md`。
动态 Geometry Nodes 字段见 `docs/CMask_Geometry_Nodes_动态字段.md`。

## 本地验证

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe' `
  --background --factory-startup --python tests\run_core_tests.py
```

## 一键测试与发布

仓库内的发布脚本会在 Blender 4.5、5.0、5.2 上运行测试，验证源码与最终安装
ZIP，并在三个完全隔离的用户配置中实际安装和加载扩展。随后生成安装包、完整
交付包及 SHA256 校验文件：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release.ps1
```

加入 `-FullRenderMatrix` 可同时运行完整真实渲染矩阵；已经单独完成测试、只需
重新构建时可使用 `-SkipTests`。发布产物位于 `dist`。

## 安装

开发期间可将 `collection_mask_exporter` 目录打包为 ZIP，然后在 Blender 的
“首选项 → 扩展 → 从磁盘安装”中选择该 ZIP。

## 许可证与版权

CMask 版权归 `kaliwill` 及各贡献者所有，采用
`GNU General Public License v3.0 or later`（SPDX：`GPL-3.0-or-later`）发布。
完整条款见 [LICENSE](LICENSE)，运行时及测试相关的第三方软件说明见
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)。

所有 Python 源文件均包含 SPDX 版权与许可证声明。Blender、Python、
OpenImageIO 和 Adobe Photoshop 不随本项目打包，分别受其自身许可证或使用
条款约束。
