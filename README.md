# ComfyUI-PSD2Layer

PSD ↔ 图层图像管线**双向转换**的 ComfyUI 自定义节点。

## 节点

### 1. Load PSD File (`PSD2Layer/Load PSD File`)
解析 PSD 路径，输出 `PSD` 引脚供下游使用（路径只在此处填写一次）。

| 参数 | 说明 |
|------|------|
| `psd_file` | PSD 路径（绝对路径，或相对 ComfyUI `input/`） |

- 输出 `psd`：`PSD` 类型引用 → 接 **PSD to Layers** 或 **Merge PSD Files**

### 2. PSD to Layers (`PSD2Layer/PSD to Layers`)
将 `PSD` 引用拆为图层图像 + `LAYER_INFO`。

| 参数 | 说明 |
|------|------|
| `psd` | **必填**，来自 Load PSD File |
| `include_hidden` | 默认 True |
| `background` | `none` / `black` / `white` / `gray` |

- 输出 `layer_image`、`layer_info`（列表）

### 3. Merge Layer Images
处理后的 RGB 与旁路 alpha 合并（见节点内参数）。

### 4. Rebuild PSD from Layers
按 `layer_info` 归位写入 PSD（图像尺寸与 alpha 由输入决定）。

### 5. Merge PSD Files
合并多个 `PSD`；**每个源文件一个组**（组名 = 文件名），可调 XY 偏移。

| 参数 | 说明 |
|------|------|
| `psd_1` ~ `psd_5` | Load PSD File；`psd_1` 必填 |
| `offset_x_1` ~ `offset_x_5` | 该 PSD 在合并画布上的 X 偏移 |
| `offset_y_1` ~ `offset_y_5` | 该 PSD 在合并画布上的 Y 偏移 |
| `output_dir` / `filename` | 保存路径 |
| `canvas_width/height` | `0` = 按图层外包自动计算 |
| `include_hidden` | 默认 True |

- 节点内嵌**预览画布**（调整 offset 自动刷新，不重跑上游；右上角「刷新」按钮）
- Queue 执行时写入最终 PSD 文件
- 源 PSD 内图层递归展开，放入以文件名命名的组中

## 典型工作流

```
Load PSD File ──psd──> PSD to Layers ──layer_image──> 处理 ──> Merge ──> Rebuild
                           └── layer_info ──────────────────────────────┘

Load PSD File ──┬──> Merge PSD Files（节点内画布调 offset）
Load PSD File ──┘     Queue 后写入最终 PSD
```

## 安装

```bash
cd ComfyUI/custom_nodes
git clone <本仓库> ComfyUI-PSD2Layer
pip install -r requirements.txt
# 重启 ComfyUI
```
