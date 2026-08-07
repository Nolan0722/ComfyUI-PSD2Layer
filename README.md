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
| **Merge PSD Files** | 1～5 个 `psd` 按序号合并到统一画布 |
| **Merge Layer Images** | 1～10 张 `IMAGE` 按序号合并为 `psd` |
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

将多个 PSD 合并到一张画布；每个源一个根组（组内保留源 PSD 的完整嵌套组结构与原始命名/属性），各源居中放置。根组名默认 `PSD_1`、`PSD_2`…，可在 `name_N` 自定义。

| 参数 | 说明 |
|------|------|
| `psd_1`～`psd_5` | `psd_1` 必填；可接 Load PSD File、Layers to PSD 等 |
| `name_1`～`name_5` | 每个源根组的组名，默认 `PSD_N`，可自行修改 |
| `canvas_width` / `canvas_height` | 画布尺寸；为 `0` 时取所有输入中的最大尺寸 |
| `include_hidden` | 合并时是否包含隐藏图层 |

**输出** `psd`

叠放顺序：`psd_1` 最上，`psd_5` 最下。

---

### Merge Layer Images

与 Merge PSD Files 同样的合成方式，但输入为 **IMAGE**（1～10 张），每张图一个图层组（组名默认 `Image_N`，可在 `name_N` 自定义）。

| 参数 | 说明 |
|------|------|
| `image_1`～`image_10` | `image_1` 必填 |
| `name_1`～`name_10` | 每张图根组的组名，默认 `Image_N`，可自行修改 |
| `canvas_width` / `canvas_height` | 画布尺寸；为 `0` 时取所有输入中的最大尺寸 |

**输出** `psd`

叠放顺序：`image_1` 最上，序号大的在下。

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
Load PSD File ──┘
```

也可将 **Layers to PSD** 的输出接入 Merge PSD Files。

### 多张图拼成 PSD

```
（任意 IMAGE 来源）──> Merge Layer Images ──psd──> Save PSD File
```

## 依赖

见 `requirements.txt`（主要为 `psd-tools`、`Pillow`、`numpy`）。
