"""ComfyUI-PSD2Layer: PSD <-> 图层图像管线双向转换自定义节点。"""
import logging
import os

logging.getLogger("psd_tools").setLevel(logging.WARNING)

from . import routes  # noqa: F401 — 注册预览 API
from .nodes import (
    PSDFileLoader,
    PSDFileSaver,
    PSDLayerExtractor,
    PSDLayerImageJoiner,
    PSDMerger,
    PSDRebuilder,
)

NODE_CLASS_MAPPINGS = {
    "PSD2Layer Load File": PSDFileLoader,
    "PSD2Layer PSD to Layers": PSDLayerExtractor,
    "PSD2Layer Apply Alpha to Layers": PSDLayerImageJoiner,
    "PSD2Layer Layers to PSD": PSDRebuilder,
    "PSD2Layer Merge PSD Files": PSDMerger,
    "PSD2Layer Save PSD File": PSDFileSaver,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSD2Layer Load File": "Load PSD File",
    "PSD2Layer PSD to Layers": "PSD to Layers",
    "PSD2Layer Apply Alpha to Layers": "Apply Alpha to Layers",
    "PSD2Layer Layers to PSD": "Layers to PSD",
    "PSD2Layer Merge PSD Files": "Merge PSD Files",
    "PSD2Layer Save PSD File": "Save PSD File",
}

WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "web", "js")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
