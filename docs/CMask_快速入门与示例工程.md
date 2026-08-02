# CMask 快速入门与示例工程

示例文件位于 `examples/CMask_Demo.blend`，可直接由正式支持的
Blender 4.5、5.0 和 5.2 打开。安装 CMask 后完整重启 Blender，再打开
该工程即可看到已经配置好的四种角色和“演示交付”预设。

## 示例内容

| Collection | 角色 | 用途 |
|---|---|---|
| `CM_Body` | MASK | 主体独立彩色 ID 和蒙版 |
| `CM_Detail` | MASK | 细节独立彩色 ID 和蒙版 |
| `CM_Occluder` | OCCLUDER | 保持前景遮挡，但不单独导出 |
| `CM_Holdout` | HOLDOUT | 从所有结果中切出透明区域 |

场景已经配置正交相机、16-bit PNG、Straight Alpha、文件名模板、JSON 报告、
Photoshop Alpha 通道和相对输出目录 `//CMask_Demo_Output/`。

## 五分钟工作流

1. 在 3D Viewport 按 `N`，选择 `Collection Mask` 标签。
2. 点击“检查场景”，确认没有错误。
3. 点击“预览彩色 ID”，观察两个 MASK 组颜色和遮挡/挖空效果。
4. 选中 `CM_Body` 或 `CM_Detail`，点击“预览选中组蒙版”。
5. 保持“蒙版使用组名”和“蒙版使用 Color ID 颜色”开启。
6. 点击“一键导出渲染 + 蒙版 + Photoshop”。输出目录会出现正式渲染、
   Color ID、`CM_Body.png`、`CM_Detail.png`、JSON 报告和 JSX。
7. 在 Photoshop 选择“文件 → 脚本 → 浏览”，运行生成的 JSX；脚本会建立
   命名图层、Alpha 通道并保存 PSD。

## 替换为自己的项目

复制或新建以 `CM_` 开头的 Collection，把对象放入对应集合，然后点击
“扫描 / 同步”。按用途设置 MASK、OCCLUDER、HOLDOUT 或 IGNORE。对象同时
属于多个启用组时，应在列表调整优先级，或启用严格模式后按检查结果整理场景。

建议正式交付前依次验证彩色 ID、VISIBLE 蒙版和 SILHOUETTE 蒙版，并保留
JSON 报告。启用组名命名时，单次蒙版文件名始终等于 Collection 组名；批量
相机/帧若发生同名路径，会自动追加相机与帧后缀。

## 重新生成示例

开发者可使用 Blender 4.5 运行：

```powershell
blender.exe --background --factory-startup --python tests/create_sample_project.py
```

生成器不会依赖现有 `.blend`，便于持续验证示例内容没有与插件版本脱节。
