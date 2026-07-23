"""ComfyUI-PSD2Layer: PSD <-> 图层图像管线双向转换自定义节点。

提供三个节点：
  - Load PSD Layers : 读 PSD，拆图层进管线 + LAYER_INFO 旁路
  - Rebuild PSD from Layers : 处理后图层按原始位置/顺序还原成 PSD
  - Merge PSD Files : 多个 PSD 合并到统一画布
"""
from .nodes import PSDLayerExtractor, PSDMerger, PSDRebuilder

NODE_CLASS_MAPPINGS = {
    "PSD2Layer Load": PSDLayerExtractor,
    "PSD2Layer Rebuild": PSDRebuilder,
    "PSD2Layer Merge": PSDMerger,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSD2Layer Load": "Load PSD Layers",
    "PSD2Layer Rebuild": "Rebuild PSD from Layers",
    "PSD2Layer Merge": "Merge PSD Files",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
