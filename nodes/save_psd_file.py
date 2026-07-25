"""节点：Save PSD File — 将 PSD 引用写入磁盘。"""
from __future__ import annotations

from ..utils import psd_io


class SavePSDFile:
    """接收 PSD 引用，按 output_dir + filename 保存文件。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "psd": (psd_io.PSD_TYPE, {"forceInput": True}),
                "output_dir": ("STRING", {"default": "", "multiline": False}),
                "filename": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "PSD2Layer"

    def save(self, psd, output_dir, filename):
        psd_image = psd_io.resolve_psd_image(psd)
        path = psd_io.resolve_save_path(output_dir, filename, default_stem="saved")
        psd_io.save_psd(psd_image, path)
        return ()
