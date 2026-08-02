# CMask Blender API 兼容性诊断

CMask v0.4.6 提供不依赖渲染相机的一键环境诊断，适合升级 Blender、部署
渲染农场节点或安装新插件版本后执行。

## 使用方式

在 CMask 面板的“冲突检查”区域点击“API 兼容性诊断”。报告写入：

```text
CMask_Output/Reports/<blend>_compatibility_report.json
```

后台节点可运行：

```powershell
blender.exe project.blend --background --python-expr `
  "from collection_mask_exporter.cli import main; main()" -- `
  --operation diagnose --output D:\CMask_Output
```

## 检查项目

| Key | 等级 | 影响 |
|---|---|---|
| `view_layer_create_remove` | 必需 | 临时 View Layer 生命周期 |
| `view_layer_material_override` | 必需 | 非破坏性 Emission 覆盖 |
| `layer_collection_flags` | 必需 | Exclude、Holdout 与遮挡 |
| `material_node_tree` | 必需 | 临时材质节点树 |
| `render_image_settings` | 必需 | PNG/OpenEXR 格式和位深 |
| `compositor_api` | 可选 | 自动创建 Compositor 节点 |
| `openimageio` | 可选 | Multilayer EXR 与 Cryptomatte |

`compatible=false` 表示至少一个必需能力缺失，不应执行正式导出。可选检查失败
不会影响普通 PNG 蒙版，但应停用对应高级功能。

## 版本状态

- `SUPPORTED`：位于当前正式支持范围并通过能力检查。
- `UNSUPPORTED`：低于 Blender 4.5，不属于正式支持范围。
- `UNVALIDATED`：不属于 4.5.x、5.0.x、5.2.x 正式验证版本线。
- `FUTURE_UNVALIDATED`：Blender 6.0 或更高版本，关键能力存在，但尚未完成该
  正式版本的全套真实渲染矩阵。

`compatible=true` 仅表示本次检查的关键 API 存在，不等同于该 Blender 版本
已经正式受支持。面板会对 `UNSUPPORTED`、`UNVALIDATED` 和
`FUTURE_UNVALIDATED` 使用警告措辞。

这种区分避免把“API 名称仍存在”误认为“完整渲染行为已经验证”。
