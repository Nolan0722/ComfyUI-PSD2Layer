# 参考资料 (Reference) 导航

ComfyUI-PSD2Layer 插件开发的官方规范与参考实现。所有路径相对本仓库根。

## 目录结构

```
reference/
├── comfyui_official_docs/    # ComfyUI 官方文档 (Comfy-Org/docs) — 克隆可能因网络失败
├── reference_projects/       # 相关 ComfyUI 自定义节点（已克隆）
│   ├── ComfyUI-Layers/           # 写 PSD (pytoshop)，全画布无 offset
│   ├── layerdivider/             # 写 PSD (pytoshop)，offset 仍为 0
│   ├── ComfyUI-LayerDivider/     # layerdivider 的 ComfyUI 封装
│   ├── ComfyUI_LayerStyle/       # 图层工具集（LoadPSD 已迁到 Advance）
│   ├── ComfyUI_LayerStyle_Advance/ # LayerUtility: LoadPSD 源码
│   ├── comfyui_psd/              # 链式 PSDLayer + Save（psd_tools，无 offset）
│   ├── Comfyui-HAIGC-PSD/        # 读+写全套（pytoshop nested_layers，有 x/y）
│   └── comfyui_psd_smart_object/ # 智能对象 mockup（读 PSD，非通用拆层）
├── libraries/
│   └── psd-tools/            # 主用库源码
└── README.md                 # 本文件
```

---

## 1. ComfyUI 官方开发规范（权威来源）

仓库名纠正记录：官方文档是 `Comfy-Org/docs`（非 comfyui_docs）。

**中文版**（优先看）— 路径前缀 `comfyui_official_docs/zh/`，英文版去掉 `zh/`：

| 主题 | 路径 |
|------|------|
| 自定义节点入门（结构/INPUT_TYPES/RETURN_TYPES/FUNCTION/CATEGORY） | `zh/custom-nodes/walkthrough.mdx` |
| 节点属性（OUTPUT_IS_LIST / INPUT_IS_LIST / 生命周期） | `zh/custom-nodes/backend/server_overview.mdx` |
| **自定义数据类型（任意 Python 对象传递��forceInput）** | `zh/custom-nodes/backend/more_on_inputs.mdx` |
| **List 处理（变量尺寸图像、map_node_over_list）** | `zh/custom-nodes/backend/lists.mdx` |
| 数据类型（IMAGE/MASK 张量约定） | `zh/custom-nodes/backend/datatypes.mdx` |
| 接口规范 | `zh/custom-nodes/backend/interface.mdx` |
| 前端 JS | `zh/custom-nodes/js/javascript_overview.mdx` |

> 注：文档为 `.mdx` 格式（非 `.md`），Glob 搜 `*.md` 会漏掉。

---

## 2. 参考项目（该看哪些文件）

### ComfyUI-Layers — 写 PSD (pytoshop)
- **`reference_projects/ComfyUI-Layers/layers_creation.py`** — 全部节点实现
  - `PSDLayerCreator`（图+mask 拆层写 PSD）、`PSDLayerCreatorFromImagesOnly`（多图每张一层）
  - 学：IMAGE tensor→numpy uint8、`pytoshop.core.PsdFile`、`LayerRecord(channels={-1:alpha,0:R,1:G,2:B}, top,bottom,left,right, blend_mode, opacity)`、`psd.write(fd)`
  - 局限：所有图层 `top=0,left=0` 全画布，**无偏移**（本插件要改进这点）
- `install.py` / README — 依赖装法：`pip install pytoshop`、`pip install psd-tools --no-deps`

### layerdivider — 带 offset 的写法 (pytoshop)
- **`reference_projects/layerdivider/ldivider/ld_utils.py`** → `add_psd()` (第34行)
  - 学：`LayerRecord(top, bottom=img.shape[0], left, right=img.shape[1], ...)` —— **offset 写法的直接范本**（本插件 fallback 路径核心参考）
- `ldivider/` 下还有读 PSD / 分组的低层 `psd_tools.psd.PSD.read` 用法

### ComfyUI-LayerDivider — ComfyUI 节点封装范例
- `reference_projects/ComfyUI-LayerDivider/` — 看 `__init__.py` 的 NODE_CLASS_MAPPINGS 组织、节点如何调用 layerdivider

### ComfyUI_LayerStyle / ComfyUI_LayerStyle_Advance — 读 PSD
- LoadPSD 已迁到 **`ComfyUI_LayerStyle_Advance/py/loadpsd.py`**
- 学：`PSDImage.open`、`layer.composite()` / `topil()`、按 index/name 提取单层
- 局限：输出单图层或 flat，**无「拆全部图层 + 旁路元数据 + 精确还原」管线**

### comfyui_psd — 链式写 PSD (psd_tools)
- **`reference_projects/comfyui_psd/nodes.py`**
- 学：自定义类型 `PSD`（`PSDData` 类链式 append）、`PixelLayer.frompil` + `psd.append`
- 局限：画布 = 最大图层尺寸，**所有层 top/left=0**，无 offset

### Comfyui-HAIGC-PSD — 读+写全套 (pytoshop)
- **`haigc_psd.py`**（约 3400 行，功能最全）
- 读：`HAIGC_LoadPSD` — `PSDImage.open`，支持「按PSD原位置」/「完整原图层」两种输出模式
- 写：`HAIGC_SavePSD` — `nested_layers.nested_layers_to_psd()`，图层 dict 含 `x/y/width/height`
- 学：混合模式中英映射、背景适应、批次分组、图层样式栅格化
- 局限：元数据走 `PSD_LAYERS` dict 链，**非独立旁路端口**；写路径用 pytoshop 而非 psd_tools

### comfyui_psd_smart_object — 智能对象 mockup
- **`psd_mockup_node.py`** — 读 PSD 智能对象层，把图片投影到 mockup
- 学：`SmartObjectLayer`、transform box、PSD 上传前端
- 局限：**非通用拆层/还原**，专用于 mockup 替换

---

## 5. 竞品对比与本项目定位

| 插件 | 读 PSD | 写 PSD | offset 定位 | 旁路元数据 | 处理后还原 |
|------|--------|--------|-------------|------------|------------|
| ComfyUI-Layers | ✗ | ✓ pytoshop | ✗ (0,0) | ✗ | ✗ |
| layerdivider | 部分 | ✓ pytoshop | ✗ (0,0) | ✗ | ✗ |
| comfyui_psd | ✗ | ✓ psd_tools | ✗ | ✗ | ✗ |
| LayerStyle LoadPSD | ✓ psd_tools | ✗ | 读时有 bbox | ✗ | ✗ |
| HAIGC-PSD | ✓ psd_tools | ✓ pytoshop | ✓ x/y | PSD_LAYERS 链 | 需整条 HAIGC 管线 |
| **ComfyUI-PSD2Layer** | ✓ psd_tools | ✓ psd_tools | ✓ top/left | **LAYER_INFO 旁路** | **Load→任意处理→Rebuild** |

**本项目的核心差异**：`LAYER_INFO` 自定义类型作为独立端口旁路，处理节点只碰 `IMAGE`，位置/alpha/属性不经过处理黑盒，Rebuild 时按 `top/left` + 自动 scale 精确还原。


## 3. psd-tools 库（主用）

### 关键 API 源码位置（已验证存在）
| API | 位置 |
|-----|------|
| `create_pixel_layer(image, name, top, left, compression, opacity, blend_mode)` | `libraries/psd-tools/src/psd_tools/api/psd_image.py:691` |
| `PSDImage.frompil` | `psd_image.py:178` |
| `Layer.composite()` | `api/layers.py:743` |
| `Layer.topil()` | `api/layers.py:705` |
| 使用指南 | `libraries/psd-tools/docs/usage.rst` |

### 已验证的 `create_pixel_layer` 签名（本插件"节点2 还原"核心）
```python
psd.create_pixel_layer(
    pil_image,                  # PIL.Image (RGBA → alpha 自动作透明通道)
    name="Layer",
    top=0, left=0,              # ← 偏移定位 (本插件关键)
    compression=Compression.RLE,
    opacity=255,                # int 0-255
    blend_mode=BlendMode.NORMAL # BlendMode 枚举
) -> PixelLayer
```
内部 `append` 到 PSDImage。**注意顺序**：连续 create，第一个图层最终在**底部**（与 `for layer in psd` 的 bottom→top 一致；实现时需验证）。

---

## 4. 开发规范速查（节点最小结构）

```python
class MyNode:
    CATEGORY = "PSD2Layer"
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {...}, "optional": {...}}
    RETURN_TYPES = ("IMAGE",)      # 自定义类型如 "LAYER_INFO" 也合法
    RETURN_NAMES = ("out",)
    FUNCTION = "execute"           # 执行方法名
    OUTPUT_IS_LIST = (False,)      # True → 返回的 list 展开为序列逐项流过下游
    INPUT_IS_LIST = False          # True → 一次性收到整个 list
    def execute(self, ...):
        return (result,)           # 必须是 tuple
```
`__init__.py` 导出 `NODE_CLASS_MAPPINGS`（dict: 唯一id→类）+ `NODE_DISPLAY_NAME_MAPPINGS`。

自定义类型端口需 `forceInput`（前端无 widget）：
```python
"layer_info": ("LAYER_INFO", {"forceInput": True})
```

---

## 来源
- ComfyUI 官方文档: https://github.com/Comfy-Org/docs
- ComfyUI-Layers: https://github.com/alessandrozonta/ComfyUI-Layers
- layerdivider: https://github.com/mattyamonaca/layerdivider
- ComfyUI-LayerDivider: https://github.com/jtydhr88/ComfyUI-LayerDivider
- ComfyUI_LayerStyle: https://github.com/chflame163/ComfyUI_LayerStyle
- ComfyUI_LayerStyle_Advance: https://github.com/chflame163/ComfyUI_LayerStyle_Advance
- comfyui_psd: https://github.com/sugarkwork/comfyui_psd
- Comfyui-HAIGC-PSD: https://github.com/HAIGC/Comfyui-HAIGC-PSD
- comfyui_psd_smart_object: https://github.com/leafiy/comfyui_psd_smart_object
- psd-tools: https://github.com/psd-tools/psd-tools
