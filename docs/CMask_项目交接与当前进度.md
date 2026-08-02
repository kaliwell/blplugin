# CMask 项目交接与当前进度

> 交接日期：2026-08-02
> 当前版本：v0.9.0
> 项目目录：`D:\blplugin`
> 正式支持：Blender 4.5.x、5.0.x、5.2.x
> 最新验证矩阵：Blender 4.5.12 LTS、5.0.1、5.2.0 LTS

## 1. 交接结论

Collection Mask Exporter 当前已经形成可安装、可使用、可测试的完整 Blender
Extension。以 v0.9.0 已定义的功能范围计算，核心交付流程已完成；剩余工作主要是
Blender 6.0 正式版发布后的实机认证、更多动态 Geometry Nodes 数据域，以及持续的
UI/Photoshop 跨版本兼容维护。

当前可直接交付的安装包与完整交付包：

```text
D:\blplugin\dist\collection_mask_exporter-0.9.0.zip
D:\blplugin\dist\collection_mask_exporter-0.9.0-release.zip
```

对应 SHA256 统一记录在：

```text
D:\blplugin\dist\collection_mask_exporter-0.9.0-SHA256.txt
```

最终安装 ZIP 已分别通过 Blender 4.5、5.0、5.2 的清单验证，以及隔离用户配置下
的真实安装、启用与模块加载烟雾测试。`collection_mask_exporter-0.6.0-release.zip`
属于旧包，不应继续交付。

## 2. 当前完成度

| 模块 | 状态 | 说明 |
|---|---|---|
| Collection 扫描、角色与冲突解析 | 已完成 | 前缀、顶级、手动、嵌套、优先级、UUID 持久化 |
| Color ID 与独立蒙版 | 已完成 | VISIBLE、SILHOUETTE、PNG、EXR |
| Multilayer EXR / Cryptomatte | 已完成 | half/float、多层 RGBA、Collection manifest |
| 相机/帧批量导出 | 已完成 | 路径消歧、状态恢复、JSON 报告 |
| Collection Instance | 已完成 | 宿主归属、嵌套源、冲突与状态恢复 |
| Geometry Nodes 静态源 | 已完成 | 输出可达分析、嵌套组、静态源拆分 |
| Geometry Nodes 动态字段 | 已完成当前协议 | Blender 5.0+，求值后 Mesh FACE/INT `cmask_id` |
| 中英文界面 | 已完成 | 跟随 Blender，兼容 `zh_CN` 与 `zh_HANS` |
| 可折叠侧栏布局 | 已完成 | 原生父/子面板，常用区展开、低频区折叠 |
| Photoshop 自动交付 | 已完成并实机验证 | v0.6.6：6 图层、5 Alpha、PSD 保存通过 |
| 一键渲染与 PS 交付 | 已完成 | 正式渲染、Color ID、组名彩色蒙版、JSX 与清单 |
| CLI / 渲染农场 | 已完成 | JSON 任务、结果 JSON、诊断操作 |
| 发布许可证与版权 | 已完成 | GPL-3.0-or-later、第三方清单、53 个 Python 文件 SPDX 头 |
| Blender 6.0 正式版认证 | 待执行 | 正式版尚未纳入当前实机矩阵 |

## 3. 最近版本变更

### v0.6.0

- 新增 Blender 5.0+ 求值后动态 GN 属性协议。
- 每次渲染读取最终 Mesh 的 FACE 域 INT 属性，默认名称为 `cmask_id`。
- 支持由驱动、逐帧字段、Simulation Zone、Repeat Zone 产生的最终结果语义。
- 动态 ID 纳入场景检查、预设、CLI 和 JSON 报告。
- 新增简体中文 / English 自动语言适配。

### v0.6.1

- 修复 Blender 5.2 `UILayout.prop_search` 参数不兼容。
- 原现象：面板只绘制到“预设”，控制台提示 `text` 必须使用关键字参数。

### v0.6.2

- 将 Blender 5.2 不存在的 `MOD_NODES` 图标替换为 `GEOMETRY_NODES`。
- 新增面板 API、图标枚举和完整 `draw()` 路径测试。

### v0.6.3

- 修复部分 Photoshop 版本在 JSX 收尾阶段拒绝恢复
  `app.displayDialogs` 的问题。
- 恢复操作使用独立 `try/catch`；后续实机发现部分 Photoshop 仍把宿主错误作为
  不可捕获异常处理，因此该方案由 v0.6.4 取代。

### v0.6.4

- 完全移除 JSX 对全局 `app.displayDialogs` 的读取、关闭和恢复。
- `executeAction` 继续单独使用 `DialogModes.NO`，不改变 Photoshop 应用级状态。

### v0.6.5

- Alpha 创建前激活复合颜色通道、清空选择并使用复制返回的准确图层引用。
- 透明度 Action 改为 stringID 写法。
- 单个 Alpha 创建失败时记录错误并继续保存分层 PSD，不再取消整个导入任务。

### v0.6.6

- 检测完全透明、无像素边界的蒙版，直接创建全黑 Alpha 通道。
- 避免空图层触发 Photoshop“载入透明度/设置命令不可用”。

### v0.7.0

- 正式支持范围收紧为 Blender 4.5.x、5.0.x、5.2.x。
- Extension 最低安装版本提高到 Blender 4.5.0。
- 兼容性诊断对 5.1、5.3 等非发布矩阵版本线标记 `UNVALIDATED`。

### v0.8.0

- 蒙版文件、Photoshop 图层和 Alpha 通道默认直接使用 Collection 组名。
- 蒙版 RGB 与对应组的 Color ID 颜色一致，精确 Alpha、边缘调整和预乘仍保留。
- 新增“一键导出渲染 + 蒙版 + Photoshop”：正式渲染、Color ID、全部 MASK、
  JSX、交接清单和 JSON 报告一次完成。
- CLI 新增 `delivery` 操作。

### v0.8.1

- 补齐 Blender `Operator` 专用翻译上下文，修复面板按钮仍显示英文。
- 翻译面板标题并优化透明度存储标签。
- 未实际保存的旧 `Default Preset` 占位迁移为语言中性的 `CMask`。

### v0.9.0

- 将原有单一长面板拆分为 1 个父面板和 9 个 Blender 原生可折叠子面板。
- 默认展开扫描与组、输出设置和一键交付；低频工具默认折叠。
- 新增子面板标题中英文翻译和跨 Blender 4.5/5.0/5.2 层级、绘制回归测试。

## 4. 关键工作流

### 常规 Collection 导出

1. 在 `3D Viewport > N 面板 > Collection Mask` 打开插件。
2. 扫描或手动添加 Collection。
3. 设置 MASK / HOLDOUT / OCCLUDER / IGNORE 角色。
4. 执行“检查场景”。
5. 导出 Color ID、选中蒙版、全部蒙版或批量相机/帧。

### 动态 Geometry Nodes

1. Geometry Nodes 宿主所在 CMask 组设为 IGNORE。
2. 输出组分别设置唯一正整数“动态 GN ID”。
3. 在节点树最终输出前写入 FACE 域 INT 属性 `cmask_id`。
4. 使用实例时先 `Realize Instances`，保证属性最终落在 Face 域。
5. 启用“动态 GN 属性”并检查场景。

动态模式不会猜测节点意图。只有最终求值 Mesh 上明确存在的属性才参与拆分。
详见 [CMask_Geometry_Nodes_动态字段.md](CMask_Geometry_Nodes_动态字段.md)。

### Photoshop 自动交付

1. 先成功导出 Color ID 或 Mask。
2. 保持“Photoshop 创建 Alpha 通道”开启。
3. 点击“生成 Photoshop 导入脚本”。
4. 在 Photoshop 使用“文件 > 脚本 > 浏览”运行输出目录中的 `*_import.jsx`。
5. JSX 自动创建图层、Alpha 通道并保存 PSD。

JSX 只使用“最近输出”，不会重新渲染。生成脚本后不要移动源 PNG/EXR。
详见 [CMask_Photoshop_交付.md](CMask_Photoshop_交付.md)。

## 5. 代码结构

```text
collection_mask_exporter/
├─ blender_manifest.toml       # Blender Extension 清单与版本
├─ constants.py                # ADDON_VERSION、角色与通用常量
├─ properties.py               # Scene、组、预设和输出属性
├─ registration.py             # 属性、操作符、UI、翻译生命周期
├─ translations.py             # English 源字符串与简体中文翻译
├─ cli.py                      # 后台任务和渲染农场入口
├─ core/
│  ├─ scanner.py               # Collection 扫描与增量同步
│  ├─ group_resolver.py        # 对象归属、实例和 GN 源解析
│  ├─ geometry_nodes.py        # 静态 GN 输出可达依赖分析
│  ├─ dynamic_geometry.py      # 求值后 cmask_id 网格拆分与清理
│  ├─ conflict_checker.py      # 场景预检和动态配置校验
│  ├─ render_pipeline.py       # 临时 View Layer、材质和渲染生命周期
│  ├─ state_manager.py         # 用户场景状态捕获与恢复
│  ├─ multilayer.py            # Multilayer EXR 合并
│  ├─ cryptomatte.py           # Collection Cryptomatte 写入
│  ├─ report_manager.py        # 导出 JSON 报告
│  └─ photoshop.py             # JSX、交接清单和 PSD 目标生成
├─ operators/                  # Blender 操作符
└─ ui/                         # N 面板、列表和 Outliner 菜单
```

## 6. 数据与状态约定

Collection 自定义属性：

| 属性 | 含义 |
|---|---|
| `cmask_uuid` | 稳定 Collection ID |
| `cmask_enabled` | 是否启用 |
| `cmask_role` | MASK / HOLDOUT / OCCLUDER / IGNORE |
| `cmask_color` | Color ID RGBA |
| `cmask_priority` | 冲突解析顺序 |
| `cmask_dynamic_id` | 动态 GN 正整数 ID；0 表示未映射 |

动态渲染临时数据以 `__CMASK_DYNAMIC` 为前缀。成功或失败后都必须清理对象、
Mesh 和 Collection。涉及渲染管线的修改必须继续验证异常路径和状态恢复。

## 7. 已完成验证

| 验证项目 | Blender 版本 | 状态 |
|---|---|---|
| 核心测试 | 4.5.12、5.0.1、5.2.0 | 通过 |
| 正式 PNG/EXR 渲染矩阵 | 4.5.12、5.0.1、5.2.0 | 通过 |
| 动态 `cmask_id` 实机渲染 | 5.0.1、5.2.0 | 通过 |
| 中英文翻译切换 | 4.5.12、5.0.1、5.2.0 | 通过 |
| 面板参数、图标与完整 draw | 4.5.12、5.0.1、5.2.0 | 通过 |
| Blender Extension validate | 5.2.0 | 通过 |
| Photoshop JSX 实机 | 用户当前 Photoshop 环境 | v0.6.6：6 图层、5 Alpha 通道及 PSD 保存通过 |

主要测试文件：

| 文件 | 范围 |
|---|---|
| `tests/run_core_tests.py` | 扫描、冲突、预设、CLI 配置、报告、Photoshop 生成器 |
| `tests/run_render_tests.py` | PNG/EXR、Alpha、透明材质、多层、Crypto、批量、恢复 |
| `tests/run_instance_tests.py` | Collection Instance |
| `tests/run_geometry_nodes_tests.py` | GN 静态依赖 |
| `tests/run_geometry_nodes_split_tests.py` | 单宿主静态源拆分 |
| `tests/run_dynamic_geometry_tests.py` | FACE/INT 动态 ID、缺失属性、重复 ID、清理 |
| `tests/run_translation_tests.py` | en_US、zh_CN/zh_HANS |
| `tests/run_panel_api_tests.py` | prop_search、图标枚举、完整面板 draw |
| `tests/run_cli_tests.py` | 后台 JSON 任务真实导出 |

## 8. 常用验证命令

以下命令在 `D:\blplugin` 执行：

```powershell
# Blender 5.2 核心测试
& 'D:\blplugin\blendertestversion\5.2\blender-5.2.0-windows-x64\blender.exe' `
  --background --factory-startup --python tests\run_core_tests.py

# 动态 Geometry Nodes 实机测试
& 'D:\blplugin\blendertestversion\5.2\blender-5.2.0-windows-x64\blender.exe' `
  --background --factory-startup --python tests\run_dynamic_geometry_tests.py

# 面板 API 与完整绘制路径
& 'D:\blplugin\blendertestversion\5.2\blender-5.2.0-windows-x64\blender.exe' `
  --background --factory-startup --python tests\run_panel_api_tests.py

# 中英文切换
& 'D:\blplugin\blendertestversion\5.2\blender-5.2.0-windows-x64\blender.exe' `
  --background --factory-startup --python tests\run_translation_tests.py

# 扩展清单验证
& 'D:\blplugin\blendertestversion\5.2\blender-5.2.0-windows-x64\blender.exe' `
  --command extension validate collection_mask_exporter
```

## 9. 构建发布包

1. 同步修改以下两个版本号：

   - `collection_mask_exporter/constants.py` 的 `ADDON_VERSION`
   - `collection_mask_exporter/blender_manifest.toml` 的 `version`

2. 更新测试中的报告版本断言和文档版本。
3. 至少运行核心、面板、翻译以及与本次改动相关的真实渲染测试。
4. 构建：

```powershell
& 'D:\blplugin\blendertestversion\5.2\blender-5.2.0-windows-x64\blender.exe' `
  --command extension build --source-dir collection_mask_exporter --output-dir dist
```

5. 验证最终 ZIP，而不只验证源码目录：

```powershell
& 'D:\blplugin\blendertestversion\5.2\blender-5.2.0-windows-x64\blender.exe' `
  --command extension validate dist\collection_mask_exporter-X.Y.Z.zip
```

6. 计算 SHA256 并写入交接或发布说明。

目前以上步骤已整合为可重复执行的发布脚本：

```powershell
# 标准测试、构建、三版本干净安装验证和打包
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release.ps1

# 发布前同时执行三版本完整真实渲染矩阵
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\release.ps1 -FullRenderMatrix
```

v0.9.0 当前发布产物：

- `dist/collection_mask_exporter-0.9.0.zip`：Blender 从磁盘安装包。
- `dist/collection_mask_exporter-0.9.0-release.zip`：README、CHANGELOG、全部文档、
  示例工程和安装包组成的完整交付包。
- `dist/collection_mask_exporter-0.9.0-SHA256.txt`：上述两个 ZIP 的 SHA256。

## 10. 已知边界与风险

- 正式最低版本为 Blender 4.5.0，仅支持 4.5.x、5.0.x、5.2.x 发布矩阵。
- Blender 6.0 正式版尚未完成真实渲染矩阵，不能仅凭 API 名称仍存在就宣称支持。
- 动态 GN 当前只读取求值后 Mesh 的 FACE 域 INT 属性，不直接解释 INSTANCE 域、
  Point/Edge/Corner 域或任意字段业务意图。
- `cmask_id <= 0` 不映射；未配置的正整数值会忽略；同一正整数不能分配给多个组。
- 拆分 Color ID 暂不提供 Render Result 预览，应检查实际导出文件。
- 透明材质“排除对象”是对象级策略，不是纹理 Alpha 的逐像素语义分析。
- Photoshop 是否能直接打开 OpenEXR 取决于 Photoshop 版本；通用交付优先使用
  16-bit PNG。
- 更新扩展后应完整退出并重启 Blender，避免旧 Python 模块继续驻留。
- `main` 分支、本地 Git 作者、忽略规则、属性规则和 CHANGELOG 已配置，v0.7.0
  已有发布提交和标签；v0.8.0 完成验证后应创建对应提交和标签。

## 11. 下一阶段建议

优先级从高到低：

1. Blender 6.0 正式版发布后执行核心、面板、GN、渲染和示例工程完整矩阵。
2. 扩展动态 GN 协议：评估 INSTANCE 域或 GeometrySet 实例引用的稳定映射方案。
3. 增加真实 Photoshop 版本矩阵，记录 Windows/macOS、版本和 EXR 支持差异。
4. 继续把底层少量中文异常文本迁入翻译表，使非 UI 错误也完全双语化。

## 12. 相关文档

- [CMask_实现状态与使用说明.md](CMask_实现状态与使用说明.md)
- [CMask_快速入门与示例工程.md](CMask_快速入门与示例工程.md)
- [CMask_Geometry_Nodes_静态源拆分.md](CMask_Geometry_Nodes_静态源拆分.md)
- [CMask_Geometry_Nodes_动态字段.md](CMask_Geometry_Nodes_动态字段.md)
- [CMask_Photoshop_交付.md](CMask_Photoshop_交付.md)
- [CMask_命令行与渲染农场.md](CMask_命令行与渲染农场.md)
- [CMask_兼容性诊断.md](CMask_兼容性诊断.md)
