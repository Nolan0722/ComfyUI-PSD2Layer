"""LAYER_INFO 图层元数据结构。

LAYER_INFO 是 ComfyUI 自定义数据类型（任意 Python 对象），承载单个 PSD 图层的
几何与属性信息，用于在节点间旁路传递——绕过用户中间的处理步骤，保证还原时
位置/顺序/属性不丢失。
"""
from __future__ import annotations

from typing import Any

import torch

# ComfyUI 自定义类型名（节点 RETURN_TYPES / INPUT_TYPES 中使用）
LAYER_INFO_TYPE = "LAYER_INFO"


def make_layer_info(
    *,
    left: int,
    top: int,
    width: int,
    height: int,
    opacity: int,
    blend_mode: str,
    name: str,
    visible: bool,
    alpha: torch.Tensor | None,
    canvas_w: int,
    canvas_h: int,
) -> dict[str, Any]:
    """构造单层 LAYER_INFO 字典。

    alpha: 该图层原始 alpha 张量 [H,W]（float 0-1），供还原节点在
           alpha_source='original' 时还原图层形状。可为 None。
    canvas_w/canvas_h: 原 PSD 画布尺寸，冗余编码以便还原节点取默认画布。
    """
    return {
        "left": int(left),
        "top": int(top),
        "width": int(width),
        "height": int(height),
        "opacity": int(opacity),
        "blend_mode": str(blend_mode),
        "name": str(name),
        "visible": bool(visible),
        "alpha": alpha,
        "canvas_w": int(canvas_w),
        "canvas_h": int(canvas_h),
    }


def is_layer_info(obj: Any) -> bool:
    """判断对象是否为合法的 LAYER_INFO 字典。"""
    return isinstance(obj, dict) and "left" in obj and "top" in obj and "width" in obj


def estimate_scale(
    images: list[torch.Tensor], layer_infos: list[dict[str, Any]]
) -> tuple[float, float]:
    """根据第一张处理后图像尺寸 / 原始图层尺寸，推算 (sx, sy) 缩放系数。

    用于节点2 的 scale 自动检测：用户若对所有图层做了统一放大/缩小（如 2x 超分），
    offset 也需按同比例缩放，否则图层位置会错位。
    """
    if not images or not layer_infos:
        return 1.0, 1.0
    img = images[0]
    ih, iw = img.shape[-3], img.shape[-2]  # [H, W, C]
    info = layer_infos[0]
    ow, oh = info["width"], info["height"]
    sx = (iw / ow) if ow else 1.0
    sy = (ih / oh) if oh else 1.0
    return sx, sy
