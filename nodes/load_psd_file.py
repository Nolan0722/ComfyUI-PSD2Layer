"""节点：Load PSD File — 解析 PSD 路径，输出 PSD 引用供下游节点使用。"""
from __future__ import annotations

from ..utils import psd_io
from ..utils.merge_preview import get_flattened_psd


class PSDFileLoader:
    """加载 PSD 文件路径，输出 PSD 类型引脚与整图预览。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "psd_file": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = (psd_io.PSD_TYPE, "IMAGE")
    RETURN_NAMES = ("psd", "flat_preview")
    FUNCTION = "load"
    CATEGORY = "PSD2Layer"

    def load(self, psd_file):
        path = psd_io.resolve_psd_path(psd_file)
        flat = get_flattened_psd(path, include_hidden=True)
        preview = psd_io.pil_rgba_to_tensor(flat)
        return (psd_io.make_psd_ref(path), preview)
