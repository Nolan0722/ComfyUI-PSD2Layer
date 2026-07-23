# 参考资料 (Reference) 导航

ComfyUI-PSD2Layer 插件开发的官方规范与参考实现。所有路径相对本仓库根。

## 目录结构

```
reference/
├── comfyui_official_docs/    # ComfyUI 官方文档 (Comfy-Org/docs) — 含中文版
├── reference_projects/       # 4 个相关 ComfyUI 自定义节点
│   ├── ComfyUI-Layers/       #   写 PSD (pytoshop)
│   ├── layerdivider/         #   写 PSD 带 offset (pytoshop)
│   ├── ComfyUI-LayerDivider/ #   layerdivider 的 ComfyUI 封装
│   └── ComfyUI_LayerStyle/   #   读 PSD (LayerUtility: Load PSD)
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

### ComfyUI_LayerStyle — 读 PSD
- `reference_projects/ComfyUI_LayerStyle/` — `LayerUtility: Load PSD` 节点（读图层、栅格化、转 tensor 的完整路径）。代码可能在 `py/` 下编译模块，未直接 import psd_tools；作整体结构参考

---

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
- psd-tools: https://github.com/psd-tools/psd-tools
