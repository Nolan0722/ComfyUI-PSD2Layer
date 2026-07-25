# ComfyUI-PSD2Layer

在 ComfyUI 里把 PSD 拆成可逐层处理的图像，处理完再精确还原成 PSD；也支持多 PSD / 多张图合并到统一画布。

核心思路：`layer_image` 走你的处理管线，`layer_info` 旁路保存位置、尺寸、alpha、组结构——处理节点只碰图像，还原时按元数据归位。

## 安装

```bash
cd ComfyUI/custom_nodes
git clone <本仓库> ComfyUI-PSD2Layer
pip install -r requirements.txt
```

重启 ComfyUI（或刷新自定义节点）。

## 节点一览

在 ComfyUI 节点菜单 **PSD2Layer** 分类下查找：

| 节点 | 作用 |
|------|------|
| **Load PSD File** | 填写 PSD 路径，输出 `psd` 引用 + 整图预览 |
| **PSD to Layers** | `psd` → 图层图像列表 + `layer_info` 列表 |
| **Apply Alpha to Layers** | 处理后的 RGB + 旁路 alpha 合并为图层图像 |
| **Layers to PSD** | 图层图像 + `layer_info` → `psd` + 压平预览 |
| **Merge PSD Files** | 1～5 个 `psd` 合并到统一画布（节点内可拖拽调整） |
| **Merge Layer Images** | 1～5 张 `IMAGE` 合并为 `psd`（节点内可拖拽调整） |
| **Save PSD File** | 将 `psd` 保存到磁盘 |

自定义类型：

- **PSD**：文件引用或内存 PSD，在节点间传递，无需重复填路径
- **LAYER_INFO**：单层元数据（位置、尺寸、alpha、组层级等）

---

### Load PSD File

| 参数 | 说明 |
|------|------|
| `psd_file` | PSD 路径（绝对路径，或相对 ComfyUI `input/`) |

**输出** `psd`、`flat_preview`

---

### PSD to Layers

| 参数 | 说明 |
|------|------|
| `psd` | 来自 Load PSD File 或其他输出 `psd` 的节点 |
| `include_hidden` | 是否包含隐藏图层，默认 True |
| `background` | `none` / `black` / `white` / `gray` |

**输出** `layer_image`（列表）、`layer_info`（列表，与图层一一对应）

---

### Apply Alpha to Layers

| 参数 | 说明 |
|------|------|
| `images` | 处理后的图层图像（与 `layer_info` 按索引对应） |
| `layer_info` | 来自 PSD to Layers 的旁路 |
| `background` | 输出背景：`none` 保留透明，或叠到纯色底 |
| `restore_original_scale` | True 时把图像缩回 `layer_info` 原始尺寸（超分后若要保持放大结果，请设为 False） |

**输出** `layer_image`（列表）

---

### Layers to PSD

| 参数 | 说明 |
|------|------|
| `images` | 图层图像列表 |
| `layer_info` | 旁路元数据 |
| `canvas_width` / `canvas_height` | 手动画布尺寸；`0` 则按图层外包与缩放比自动计算 |

**输出** `psd`、`flat_preview`

放大后的图层会按相对 `layer_info` 的缩放比同步调整位置与画布大小。

---

### Merge PSD Files

将多个 PSD 合并到一张画布；每个源文件一个组（组名一般为文件名）。

| 参数 | 说明 |
|------|------|
| `psd_1`～`psd_5` | `psd_1` 必填；可接 Load PSD File、Layers to PSD 等 |
| `offset_x_N` / `offset_y_N` | 该源在画布上的偏移 |
| `scale_N` / `rotation_N` | 缩放与旋转 |
| `canvas_width` / `canvas_height` | 默认 3000×6000；`0` 使用默认 |
| `include_hidden` | 合并时是否包含隐藏图层 |

**输出** `psd`

节点内嵌**交互画布**：拖动物体、角点缩放、旋转手柄；滚轮缩放视图，中键/Alt 平移。Queue 时按画布参数写入 PSD。叠放顺序：`psd_1` 最上，`psd_5` 最下。

预览说明：上游为文件路径时可直接刷新；上游为内存 `psd`（如 Layers to PSD）时需先 Queue 运行上游，再点「刷新图层」。

---

### Merge Layer Images

与 Merge PSD Files 相同的画布交互，但输入为 **IMAGE**（1～5 张）。

| 参数 | 说明 |
|------|------|
| `image_1`～`image_5` | `image_1` 必填 |
| `offset_x_N` / `offset_y_N` / `scale_N` / `rotation_N` | 同 Merge PSD Files |
| `canvas_width` / `canvas_height` | 默认 3000×6000 |

**输出** `psd`

---

### Save PSD File

| 参数 | 说明 |
|------|------|
| `psd` | 任意产生 `psd` 的节点 |
| `output_dir` | 输出目录；空则落到 `output/PSD2Layer/` |
| `filename` | 文件名；空则自动生成 |

无图像输出引脚；Queue 时写入文件。

---

## 典型工作流

### 拆层 → 处理 → 还原

```
Load PSD File ──psd──> PSD to Layers ──layer_image──> （超分 / 修图 / …）
                           │
                           └── layer_info ──> Apply Alpha to Layers
                                                    │
                                                    └──> Layers to PSD ──psd──> Save PSD File
```

`layer_info` 全程旁路，不经过图像处理节点。

### 多 PSD 拼合

```
Load PSD File ──┬──> Merge PSD Files ──psd──> Save PSD File
Load PSD File ──┘      （节点内调位置后 Queue）
```

也可将 **Layers to PSD** 的输出接入 Merge PSD Files。

### 多张图拼成 PSD

```
（任意 IMAGE 来源）──> Merge Layer Images ──psd──> Save PSD File
```

## 依赖

见 `requirements.txt`（主要为 `psd-tools`、`Pillow`、`numpy`）。
