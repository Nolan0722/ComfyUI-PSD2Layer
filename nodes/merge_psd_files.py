"""节点：Merge PSD Files — 多 PSD 按槽位序号合成到统一画布。

序号小的在上层，大的在下层；每个源居中放置、一个根组（组名可自定义）。
画布宽/高为 0 时取所有输入的最大尺寸，否则按设定值。
"""
from __future__ import annotations

from ..utils import psd_io
from ..utils.merge_compose import compose_merged_psd

_PSD_SLOTS = 5


class MergePSDFiles:
    """把多个 PSD 引用合成到统一画布；每个源一个组，序号小的在上层。"""

    @classmethod
    def INPUT_TYPES(cls):
        optional = {}
        for i in range(2, _PSD_SLOTS + 1):
            optional[f"psd_{i}"] = (psd_io.PSD_TYPE,)
            optional[f"name_{i}"] = (
                "STRING",
                {"default": f"PSD_{i}", "multiline": False},
            )
        return {
            "required": {
                "psd_1": (psd_io.PSD_TYPE, {"forceInput": True}),
                "name_1": ("STRING", {"default": "PSD_1", "multiline": False}),
                "canvas_width": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
                "canvas_height": (
                    "INT",
                    {"default": 0, "min": 0, "max": 65536, "step": 1},
                ),
                "include_hidden": ("BOOLEAN", {"default": True}),
            },
            "optional": optional,
        }

    RETURN_TYPES = (psd_io.PSD_TYPE,)
    RETURN_NAMES = ("psd",)
    FUNCTION = "merge"
    CATEGORY = "PSD2Layer"

    def merge(self, psd_1, name_1, canvas_width, canvas_height, include_hidden, **kwargs):
        slots = [(psd_1, str(name_1 or "PSD_1"))]
        for i in range(2, _PSD_SLOTS + 1):
            ref = kwargs.get(f"psd_{i}")
            if ref is not None:
                name = str(kwargs.get(f"name_{i}") or f"PSD_{i}")
                slots.append((ref, name))
        if not slots or slots[0][0] is None:
            raise ValueError("请至少连接一个 PSD 输入")

        psd = compose_merged_psd(
            slots,
            include_hidden=include_hidden,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )
        return (psd_io.make_psd_data_ref(psd),)
