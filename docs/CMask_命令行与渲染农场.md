# CMask 命令行与渲染农场

> 适用版本：CMask v0.8.0+，Blender 4.5.x、5.0.x、5.2.x

## 1. 基本调用

插件安装并启用后，可在 PowerShell 中执行：

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe' `
  --background 'D:\Projects\shot.blend' `
  --python-expr 'from collection_mask_exporter.cli import main; main()' `
  -- `
  --operation all `
  --output 'D:\Render\shot' `
  --result-json 'D:\Render\shot\cmask_result.json'
```

源码开发环境尚未安装插件时，可先把项目根目录加入 Python 路径：

```powershell
--python-expr "import sys; sys.path.insert(0, r'D:\blplugin'); from collection_mask_exporter.cli import main; main()"
```

`--` 后面的参数由 CMask 解析。CLI 不会保存或覆盖输入 `.blend`。

## 2. 导出操作

`--operation` 支持：

| 值 | 功能 |
|---|---|
| `color-id` | 彩色 Collection ID |
| `selected-mask` | 指定 Collection 蒙版，配合 `--collection` |
| `all-masks` | 全部启用的 MASK |
| `all` | 彩色 ID 与全部 MASK |
| `delivery` | 正式渲染、Color ID、全部 MASK、Photoshop JSX 与交接清单 |
| `multilayer` | 单文件 Multilayer EXR |
| `cryptomatte` | Collection Cryptomatte |
| `batch` | 按相机和帧设置批量导出 |
| `diagnose` | 不渲染；生成 Blender API 兼容性报告 |

`diagnose` 用于农场节点上线前检查关键 Blender API 和 OpenImageIO。标准结果
中的 `outputs` 为空，`diagnostic_report` 指向生成的兼容性 JSON。

常用覆盖参数：

```text
--scene Scene
--preset 交付设置
--scan-mode PREFIX|TOP_LEVEL|MANUAL
--prefix CM_
--visible-only
--format PNG|OPEN_EXR
--depth 8|16|32
--mask-mode VISIBLE|SILHOUETTE
--cryptomatte-depth 2|4|6|8|10|12
--all-cameras
--frame-range START END STEP
--no-report
```

## 3. JSON 任务

任务文件是单个 JSON 对象。显式命令行参数优先于任务文件：

```json
{
  "scene": "Scene",
  "preset": "交付设置",
  "operation": "batch",
  "output_directory": "D:/Render/shot",
  "scan_mode": "PREFIX",
  "collection_prefix": "CM_",
  "scan_visible_only": true,
  "camera_mode": "ALL",
  "frame_mode": "RANGE",
  "frame_start": 1,
  "frame_end": 120,
  "frame_step": 1,
  "write_report": true,
  "result_json": "D:/Render/shot/cmask_result.json"
}
```

调用：

```powershell
& $blender --background $blend `
  --python-expr 'from collection_mask_exporter.cli import main; main()' `
  -- --job 'D:\Jobs\shot_cmask.json'
```

任务文件支持所有场景设置字段，包括 `conflict_mode`、`edge_adjustment`、
`alpha_mode`、`mask_use_group_name`、`mask_use_group_color`、
`transparent_material_mode`、`filename_template`、
`multilayer_include_color_id`、`cryptomatte_depth` 和
`geometry_nodes_split_sources`。未知字段会直接报错，
避免拼写错误被静默忽略。

## 4. 调度器集成

成功或失败都会向标准输出写一行：

```text
CMASK_CLI_RESULT={"success":true,"outputs":[...]}
```

指定 `--result-json` 后，同一信息也会写入文件。成功结果包含插件与 Blender
版本、工程、场景、操作、状态、输出列表和耗时；失败结果包含 `success: false`
及 `error`。失败默认以状态码 `2` 退出，农场调度器应同时检查进程状态码和
结果 JSON 的 `success` 字段。

建议每个农场任务使用独立输出目录和结果文件。多节点拆帧时，为每个任务设置
互不重叠的 `frame_start`、`frame_end`，并在命名模板中保留 `{frame}` 和
`{camera}`，避免不同节点写入同一路径。
