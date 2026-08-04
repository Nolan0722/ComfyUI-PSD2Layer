"""节点：Merge Layer Images — 多张 IMAGE 合并到统一画布，输出 PSD。

节点内嵌交互画布（拖动 / 旋转 / 缩放）；变换同步到隐藏参数，Queue 时写入 PSD。
"""
from __future__ import annotations

from ..utils import psd_io
from ..utils.merge_compose import compose_merged_images
from ..utils.merge_preview import save_node_flat_preview_ui

_SLOT_COUNT = 10
_TRANSFORM_WIDGET = ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.01})
_ROTATION_WIDGET = (
    "FLOAT",
    {"default": 0.0, "min": -360.0, "max": 360.0, "step": 0.1},
)
_OFFSET_WIDGET = ("INT", {"default": 0, "min": -65536, "max": 65536, "step": 1})


def _slot_transform_inputs(i: int) -> dict:
    return {
        f"offset_x_{i}": _OFFSET_WIDGET,
        f"offset_y_{i}": _OFFSET_WIDGET,
        f"scale_{i}": _TRANSFORM_WIDGET,
        f"rotation_{i}": _ROTATION_WIDGET,
    }


class MergeLayerImages:
    """把多张 IMAGE 合并到统一画布；每张图一个图层组，画布内可调变换。"""

    @classmethod
    def INPUT_TYPES(cls):
        required = {
            "image_1": ("IMAGE", {"forceInput": True}),
            **_slot_transform_inputs(1),
            "canvas_width": (
                "INT",
                {"default": 3000, "min": 0, "max": 65536, "step": 1},
            ),
            "canvas_height": (
                "INT",
                {"default": 6000, "min": 0, "max": 65536, "step": 1},
            ),
        }
        optional = {}
        for i in range(2, _SLOT_COUNT + 1):
            optional[f"image_{i}"] = ("IMAGE",)
            optional.update(_slot_transform_inputs(i))
        return {
            "required": required,
            "hidden": {"unique_id": "UNIQUE_ID"},
            "optional": optional,
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
        unique_id=None,
        **kwargs,
    ):
        entries = [
            (image_1, offset_x_1, offset_y_1, scale_1, rotation_1, "Image_1"),
        ]
        for i in range(2, _SLOT_COUNT + 1):
            entries.append(
                (
                    kwargs.get(f"image_{i}"),
                    kwargs.get(f"offset_x_{i}", 0),
                    kwargs.get(f"offset_y_{i}", 0),
                    kwargs.get(f"scale_{i}", 1.0),
                    kwargs.get(f"rotation_{i}", 0.0),
                    f"Image_{i}",
                )
            )
        slots = _active_image_slots(*entries)
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
