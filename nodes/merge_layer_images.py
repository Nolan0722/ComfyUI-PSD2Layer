"""节点：Merge Layer Images — 多张 IMAGE 合并到统一画布，输出 PSD。

节点内嵌交互画布（拖动 / 旋转 / 缩放）；变换同步到隐藏参数，Queue 时写入 PSD。
"""
from __future__ import annotations

from ..utils import psd_io
from ..utils.merge_compose import compose_merged_images
from ..utils.merge_preview import save_node_flat_preview_ui

_TRANSFORM_WIDGET = ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.01})
_ROTATION_WIDGET = (
    "FLOAT",
    {"default": 0.0, "min": -360.0, "max": 360.0, "step": 0.1},
)
_OFFSET_WIDGET = ("INT", {"default": 0, "min": -65536, "max": 65536, "step": 1})


class MergeLayerImages:
    """把多张 IMAGE 合并到统一画布；每张图一个图层组，画布内可调变换。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_1": ("IMAGE", {"forceInput": True}),
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
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
            "optional": {
                "image_2": ("IMAGE",),
                "offset_x_2": _OFFSET_WIDGET,
                "offset_y_2": _OFFSET_WIDGET,
                "scale_2": _TRANSFORM_WIDGET,
                "rotation_2": _ROTATION_WIDGET,
                "image_3": ("IMAGE",),
                "offset_x_3": _OFFSET_WIDGET,
                "offset_y_3": _OFFSET_WIDGET,
                "scale_3": _TRANSFORM_WIDGET,
                "rotation_3": _ROTATION_WIDGET,
                "image_4": ("IMAGE",),
                "offset_x_4": _OFFSET_WIDGET,
                "offset_y_4": _OFFSET_WIDGET,
                "scale_4": _TRANSFORM_WIDGET,
                "rotation_4": _ROTATION_WIDGET,
                "image_5": ("IMAGE",),
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
        image_1,
        offset_x_1,
        offset_y_1,
        scale_1,
        rotation_1,
        canvas_width,
        canvas_height,
        image_2=None,
        offset_x_2=0,
        offset_y_2=0,
        scale_2=1.0,
        rotation_2=0.0,
        image_3=None,
        offset_x_3=0,
        offset_y_3=0,
        scale_3=1.0,
        rotation_3=0.0,
        image_4=None,
        offset_x_4=0,
        offset_y_4=0,
        scale_4=1.0,
        rotation_4=0.0,
        image_5=None,
        offset_x_5=0,
        offset_y_5=0,
        scale_5=1.0,
        rotation_5=0.0,
        unique_id=None,
    ):
        slots = _active_image_slots(
            (image_1, offset_x_1, offset_y_1, scale_1, rotation_1, "Image_1"),
            (image_2, offset_x_2, offset_y_2, scale_2, rotation_2, "Image_2"),
            (image_3, offset_x_3, offset_y_3, scale_3, rotation_3, "Image_3"),
            (image_4, offset_x_4, offset_y_4, scale_4, rotation_4, "Image_4"),
            (image_5, offset_x_5, offset_y_5, scale_5, rotation_5, "Image_5"),
        )
        if not slots:
            raise ValueError("请至少连接一张图像到 image_1")

        psd = compose_merged_images(
            slots,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )
        flat = psd_io.flatten_psd_to_rgba(psd, include_hidden=True)
        save_node_flat_preview_ui(unique_id, flat)
        return (psd_io.make_psd_data_ref(psd),)


def _active_image_slots(*entries):
    out = []
    for img, ox, oy, sc, rot, name in entries:
        if img is None:
            continue
        pil = psd_io.tensor_to_pil_rgba(psd_io._drop_batch(img))
        out.append((pil, int(ox), int(oy), float(sc), float(rot), name))
    return out
