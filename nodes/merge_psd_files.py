"""节点：Merge PSD Files — 多 PSD 合并到统一画布，每组对应一个源文件。

节点内嵌交互画布（拖动 / 旋转 / 缩放）；变换同步到隐藏参数，Queue 时写入 PSD。
"""
from __future__ import annotations

from ..utils import psd_io
from ..utils.merge_compose import compose_merged_psd
from ..utils.merge_preview import register_node_psd_preview

_TRANSFORM_WIDGET = ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.01})
_ROTATION_WIDGET = (
    "FLOAT",
    {"default": 0.0, "min": -360.0, "max": 360.0, "step": 0.1},
)
_OFFSET_WIDGET = ("INT", {"default": 0, "min": -65536, "max": 65536, "step": 1})


class MergePSDFiles:
    """把多个 PSD 引用合并到统一画布；每个源文件一个组，画布内可调变换。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "psd_1": (psd_io.PSD_TYPE, {"forceInput": True}),
                "offset_x_1": _OFFSET_WIDGET,
                "offset_y_1": _OFFSET_WIDGET,
                "scale_1": _TRANSFORM_WIDGET,
                "rotation_1": _ROTATION_WIDGET,
                "canvas_width": (
                    "INT",
                    {"default": 3000, "min": 0, "max": 65536, "step": 1},
                ),
                "canvas_height": (
                    "INT",
                    {"default": 6000, "min": 0, "max": 65536, "step": 1},
                ),
                "include_hidden": ("BOOLEAN", {"default": True}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
            "optional": {
                "psd_2": (psd_io.PSD_TYPE,),
                "offset_x_2": _OFFSET_WIDGET,
                "offset_y_2": _OFFSET_WIDGET,
                "scale_2": _TRANSFORM_WIDGET,
                "rotation_2": _ROTATION_WIDGET,
                "psd_3": (psd_io.PSD_TYPE,),
                "offset_x_3": _OFFSET_WIDGET,
                "offset_y_3": _OFFSET_WIDGET,
                "scale_3": _TRANSFORM_WIDGET,
                "rotation_3": _ROTATION_WIDGET,
                "psd_4": (psd_io.PSD_TYPE,),
                "offset_x_4": _OFFSET_WIDGET,
                "offset_y_4": _OFFSET_WIDGET,
                "scale_4": _TRANSFORM_WIDGET,
                "rotation_4": _ROTATION_WIDGET,
                "psd_5": (psd_io.PSD_TYPE,),
                "offset_x_5": _OFFSET_WIDGET,
                "offset_y_5": _OFFSET_WIDGET,
                "scale_5": _TRANSFORM_WIDGET,
                "rotation_5": _ROTATION_WIDGET,
            },
        }

    RETURN_TYPES = (psd_io.PSD_TYPE,)
    RETURN_NAMES = ("psd",)
    FUNCTION = "merge"
    CATEGORY = "PSD2Layer"

    def merge(
        self,
        psd_1,
        offset_x_1,
        offset_y_1,
        scale_1,
        rotation_1,
        canvas_width,
        canvas_height,
        include_hidden,
        psd_2=None,
        offset_x_2=0,
        offset_y_2=0,
        scale_2=1.0,
        rotation_2=0.0,
        psd_3=None,
        offset_x_3=0,
        offset_y_3=0,
        scale_3=1.0,
        rotation_3=0.0,
        psd_4=None,
        offset_x_4=0,
        offset_y_4=0,
        scale_4=1.0,
        rotation_4=0.0,
        psd_5=None,
        offset_x_5=0,
        offset_y_5=0,
        scale_5=1.0,
        rotation_5=0.0,
        unique_id=None,
    ):
        slots = _active_slots(
            (psd_1, offset_x_1, offset_y_1, scale_1, rotation_1),
            (psd_2, offset_x_2, offset_y_2, scale_2, rotation_2),
            (psd_3, offset_x_3, offset_y_3, scale_3, rotation_3),
            (psd_4, offset_x_4, offset_y_4, scale_4, rotation_4),
            (psd_5, offset_x_5, offset_y_5, scale_5, rotation_5),
        )
        if not slots:
            raise ValueError("请至少连接一个 PSD 输出到 psd_1")

        ref_slots = [
            (ref, int(ox), int(oy), float(sc), float(rot))
            for ref, ox, oy, sc, rot in slots
        ]
        psd = compose_merged_psd(
            ref_slots,
            include_hidden=include_hidden,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )
        register_node_psd_preview(unique_id, psd)
        return (psd_io.make_psd_data_ref(psd),)


def _active_slots(*entries):
    out = []
    for ref, ox, oy, sc, rot in entries:
        if ref is None:
            continue
        out.append((ref, ox, oy, sc, rot))
    return out
