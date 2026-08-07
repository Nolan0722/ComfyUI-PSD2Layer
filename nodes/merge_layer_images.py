"""节点：Merge Layer Images — 多张 IMAGE 按槽位序号合成到统一画布。

序号小的在上层，大的在下层；每张图居中放置、一个根组（组名可自定义）。
画布宽/高为 0 时取所有输入的最大尺寸，否则按设定值。
"""
from __future__ import annotations

from ..utils import psd_io
from ..utils.merge_compose import compose_merged_images

_SLOT_COUNT = 10


class MergeLayerImages:
    """把多张 IMAGE 合成到统一画布；每张图一个图层组，序号小的在上层。"""

    @classmethod
    def INPUT_TYPES(cls):
        optional = {}
        for i in range(2, _SLOT_COUNT + 1):
            optional[f"image_{i}"] = ("IMAGE",)
            optional[f"name_{i}"] = (
                "STRING",
                {"default": f"Image_{i}", "multiline": False},
            )
        return {
            "required": {
                "image_1": ("IMAGE", {"forceInput": True}),
                "name_1": ("STRING", {"default": "Image_1", "multiline": False}),
                "canvas_width": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
                "canvas_height": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
            },
            "optional": optional,
        }

    RETURN_TYPES = (psd_io.PSD_TYPE,)
    RETURN_NAMES = ("psd",)
    FUNCTION = "merge"
    CATEGORY = "PSD2Layer"

    def merge(self, image_1, name_1, canvas_width, canvas_height, **kwargs):
        entries = [(image_1, str(name_1 or "Image_1"))]
        for i in range(2, _SLOT_COUNT + 1):
            img = kwargs.get(f"image_{i}")
            if img is not None:
                name = str(kwargs.get(f"name_{i}") or f"Image_{i}")
                entries.append((img, name))
        if not entries or entries[0][0] is None:
            raise ValueError("请至少连接一张图像到 image_1")

        slots = []
        for img, name in entries:
            pil = psd_io.tensor_to_pil_rgba(psd_io._drop_batch(img))
            slots.append((pil, name))

        psd = compose_merged_images(
            slots,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )
        return (psd_io.make_psd_data_ref(psd),)
