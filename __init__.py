"""ComfyUI-PSD2Layer: PSD <-> 图层图像管线双向转换自定义节点。"""
import logging

logging.getLogger("psd_tools").setLevel(logging.WARNING)

from .nodes import (
    ApplyAlphaToLayers,
    LayersToPSD,
    LoadPSDFile,
    MergeLayerImages,
    MergePSDFiles,
    PSDToLayers,
    SavePSDFile,
)

NODE_CLASS_MAPPINGS = {
    "PSD2Layer Load File": LoadPSDFile,
    "PSD2Layer PSD to Layers": PSDToLayers,
    "PSD2Layer Apply Alpha to Layers": ApplyAlphaToLayers,
    "PSD2Layer Layers to PSD": LayersToPSD,
    "PSD2Layer Merge PSD Files": MergePSDFiles,
    "PSD2Layer Merge Layer Images": MergeLayerImages,
    "PSD2Layer Save PSD File": SavePSDFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSD2Layer Load File": "Load PSD File",
    "PSD2Layer PSD to Layers": "PSD to Layers",
    "PSD2Layer Apply Alpha to Layers": "Apply Alpha to Layers",
    "PSD2Layer Layers to PSD": "Layers to PSD",
    "PSD2Layer Merge PSD Files": "Merge PSD Files",
    "PSD2Layer Merge Layer Images": "Merge Layer Images",
    "PSD2Layer Save PSD File": "Save PSD File",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
