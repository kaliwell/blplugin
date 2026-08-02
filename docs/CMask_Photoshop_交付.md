# CMask Photoshop 交付

CMask 可以把 Blender 的输出整理成 Photoshop 分层文件和
独立 Alpha 通道。
Blender 负责生成 JSX 和交接清单，Photoshop 负责读取图片并写出 PSD，因此
不需要额外的 PSD Python 库。

## 使用步骤

1. 保持“蒙版使用组名”和“蒙版使用 Color ID 颜色”开启。
2. 点击“一键导出渲染 + 蒙版 + Photoshop”。
3. 确认面板状态显示导出成功。
4. 打开 Photoshop，选择“文件 → 脚本 → 浏览”。
5. 选择输出目录 `Photoshop` 内的 `*_import.jsx`。

一键操作会先生成正式渲染、Color ID 和全部 MASK，再自动生成 JSX 与交接清单。
也可以沿用“全部导出 → 生成 Photoshop 导入脚本”的分步工作流。

脚本会关闭交互式格式提示，逐一打开输出文件，将它们复制到同一文档：

- `Render` 目录中的正式渲染图层命名为 `Render`。
- `Color_ID` 目录中的文件命名为 `Color ID`。
- `Masks` 目录中的文件、图层直接使用 Collection 组名。
- 启用“Photoshop 创建 Alpha 通道”时，每个 Mask 图层的透明度会保存为
  同组名 Alpha 通道，重名会自动追加数字。

完成后脚本自动保存 `*_cmask_photoshop.psd`，并显示导入图层数量和路径。

## 生成文件

```text
CMask_Output/
└─ Photoshop/
   ├─ product_cmask_photoshop_import.jsx
   ├─ product_cmask_photoshop_handoff.json
   └─ product_cmask_photoshop.psd    # 运行 JSX 后生成
```

交接 JSON 的 schema 是 `cmask.photoshop_handoff.v1`，可供资产管理或流水线
工具读取。它包含 JSX、目标 PSD、全部源输出、最终图层名和 Alpha 通道名。

## 注意事项

- 单独点击“生成 Photoshop 导入脚本”只使用最近输出，不会重新渲染；一键交付
  会重新生成正式渲染、Color ID 和全部蒙版。
- 移动或删除源 PNG/EXR 后，脚本会明确报告缺失路径并停止。
- 一批图层应具有相同分辨率、颜色模式和位深；CMask 同一次导出默认满足此条件。
- Photoshop 是否能打开 OpenEXR 取决于所安装版本和格式支持；通用交付建议使用
  16-bit PNG，浮点合成流程可继续使用 Multilayer EXR 或 Cryptomatte。
- Alpha 通道来自 Mask 图层的透明度；它保留抗锯齿和 CMask 边缘调整后的
  灰度覆盖率，而不是把边缘阈值化为黑白。
- v0.6.4 起，JSX 不再读取或修改全局 `app.displayDialogs`。打开、Action 和保存
  操作使用各自的显式参数，避免部分 Photoshop 将全局“设置”错误作为不可捕获
  异常处理。
- v0.6.5 在载入图层透明度前显式激活复合颜色通道并清空旧选择，使用复制操作
  返回的准确图层引用。单个 Alpha 通道失败不会取消整个任务，PSD 仍会保存并在
  完成提示中列出被跳过的通道。
- v0.6.6 会识别边界为空的全透明蒙版，并直接为其建立全黑 Alpha 通道；空蒙版
  是合法输出，不再触发 Photoshop“命令设置当前不可用”。
- v0.6.6 已在实际 Photoshop 环境完成 6 个图层、5 个 Alpha 通道和 PSD 自动保存
  验证。
