# ComfyUI-PSD2Layer

PSD ↔ 图层图像管线**双向转换**的 ComfyUI 自定义节点。

填补生态空白：把 PSD 的图层拆进 ComfyUI 管线，用任意插件逐张处理后，**按原始位置/顺序精确还原**回 PSD——并支持自定义画布与多 PSD 合并。

## 为什么需要它

现有 ComfyUI PSD 插件只能写"全画布、无偏移"的图层堆叠。本插件通过 **LAYER_INFO 元数据旁路**，让位置/顺序/属性信息绕过你的处理黑盒，保证还原精确。

```
[Load PSD Layers] ──layer_image──> [你的任意处理节点] ──images──┐
       └──layer_info──────────────────────────────────────────────┴──> [Rebuild PSD] ──> output.psd
```

## 节点

### 1. Load PSD Layers (`PSD2Layer/Load PSD Layers`)
读 PSD，拆出每个图层为图像 + 对应的 `LAYER_INFO`。

| 参数 | 说明 |
|------|------|
| `psd_file` | PSD 文件路径（绝对路径，或相对 ComfyUI `input/` 目录的文件名） |
| `include_hidden` | 是否包含隐藏图层（默认 False） |
| `flatten_groups` | 组图层是否作为整体合成图输出（默认 True；False 则展平为组内各独立图层） |

- 输出 `layer_image`：N 个独立 IMAGE（不同尺寸，可逐张流过下游任意插件）
- 输出 `layer_info`：N 个一一对应的 LAYER_INFO（位置/尺寸/属性元数据，**直连 Rebuild，不经过处理**）

### 2. Rebuild PSD from Layers (`PSD2Layer/Rebuild PSD from Layers`)
把处理后的图层按原始位置/顺序还原成分层 PSD。

| 参数 | 说明 |
|------|------|
| `images` | 处理后的图层图像（与 layer_info 一一对应） |
| `layer_info` | 来自 Load 节点的元数据（旁路） |
| `canvas_width/height` | 自定义画布；`0` = 自动按原画布 × 缩放跟随 |
| `scale` | offset 缩放系数；`0` = 自动检测（按首图尺寸比例推算，支持统一超分等） |
| `alpha_source` | `original`=用旁路原始 alpha 还原形状（默认，最稳健）；`processed`=用图像自带 alpha |
| `filename_prefix` | 输出文件名前缀 |

- 输出 `psd_path`：生成的 PSD 文件路径（`output/PSD2Layer/`）
- 输出 `flat_preview`：还原后的合成预览图

### 3. Merge PSD Files (`PSD2Layer/Merge PSD Files`)
多个 PSD 合并到统一画布。

| 参数 | 说明 |
|------|------|
| `psd_files` | 每行一个 PSD 路径 |
| `canvas_width/height` | 统一画布；`0` = 自动取所有图层 bbox 最大外包 |
| `filename_prefix` | 输出文件名前缀 |

各 PSD 图层按各自原始 xy 偏移贴到统一画布；按输入顺序叠加（首个 PSD 在最底）。

## 安装

```bash
cd ComfyUI/custom_nodes
git clone <本仓库> ComfyUI-PSD2Layer
cd ComfyUI-PSD2Layer
pip install -r requirements.txt   # psd-tools, numpy, Pillow（torch 由 ComfyUI 提供）
# 重启 ComfyUI
```

节点出现在 `PSD2Layer` 分类下。

## Alpha / 透明度说明

- 图层图像为 **RGBA `[H,W,4]`**（非标准 IMAGE 的 RGB，因为图层需要 alpha 表达形状）。
- 多数现代节点兼容 4 通道。若你的处理节点只接受 RGB：先用内置 `SplitImageWithAlpha` 拆 → 处理 RGB → `JoinImageWithAlpha` 合。
- **位置还原不依赖 alpha**——即使处理完全破坏了 alpha 或尺寸，`alpha_source=original` 会用旁路的原始 alpha 还原图层形状。
- 自动 `scale` 检测：对所有图层做统一放大/缩小时，offset 会按同比例缩放，位置不错位。

## 验证（金标准）

**恒等还原**：`Load PSD Layers` 的 `layer_image` **不经过任何处理**直连 `Rebuild PSD from Layers`。输出的 PSD 应与原 PSD 在图层结构、位置、尺寸、顺序、opacity、混合模式上完全一致——以此证明旁路机制正确。

再用 Photoshop / Photopea 打开输出 PSD，确认分层可编辑。

## 技术栈

- 主用 [`psd-tools`](https://github.com/psd-tools/psd-tools)：`create_pixel_layer(pil, top, left, opacity, blend_mode)` 直接支持偏移定位
- 写入 fallback：`pytoshop`（`LayerRecord` 带 top/bottom/left/right）
- 开发规范参考：[ComfyUI 官方文档](https://github.com/Comfy-Org/docs)
